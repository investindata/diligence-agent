from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from crewai.flow.flow import Flow, listen, start
from crewai.flow.persistence import persist
from datetime import datetime
from src.diligence_agent.tools.google_doc_processor import GoogleDocProcessor
import asyncio
from src.diligence_agent.schemas import ReportStructure, DataSources
from src.diligence_agent.research_flow import ResearchFlow
from src.diligence_agent.non_research_flow import NonResearchFlow
from src.diligence_agent.agents import organizer_agent, writer_agent
from src.diligence_agent.utils import (
    execute_subflows_and_map_results,
    extract_structured_output,
    fetch_slack_channel_data,
    write_section_file,
    clean_markdown_output,
    write_parsed_data_sources
)
import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)


from opik.integrations.crewai import track_crewai
track_crewai(project_name="diligence-agent")



class DiligenceState(BaseModel):
    # general info
    company_name: str = ""
    current_date: str = ""
    skip_method: bool = False
    
    # execution parameters
    batch_size: int = 2
    batch_delay: float = 0.0  # seconds
    num_search_terms: int = 5
    num_websites: int = 10

    # data sources organizer flow
    data_sources_file: str = "https://docs.google.com/document/d/1TZEg-gljazGMUuG1KWKoNc3PDHMGLahD5ofd1BoBWR8/edit?usp=sharing"
    data_sources: DataSources = DataSources(
        google_docs=[],
        pdfs=[],
        websites=[],
        slack_channels=[]
    )
    parsed_data_sources: Dict[str, str] = {}
    
    # research report structure
    report_structure: ReportStructure = ReportStructure(
        company_overview_section="",
        product_section="",
        why_interesting_section="",
        founders_section="",
        competitive_landscape_section="",
        market_section="",
        report_conclusion_section=""
    )

    

@persist(verbose=True)
class DiligenceFlow(Flow[DiligenceState]):

    @start()
    async def get_data_sources(self) -> DataSources:
        """Parse Google Doc containing data sources and return structured DataSources schema"""
        if self.state.skip_method and self.state.data_sources.google_docs:
            return self.state.data_sources
        
        # Retrieve raw content from Google Doc
        google_doc_processor = GoogleDocProcessor()
        raw_data_sources = google_doc_processor._run(self.state.data_sources_file).strip()
        print(f"📄 Raw data sources content (length: {len(raw_data_sources)}):")
        print("=" * 80)
        print(raw_data_sources)
        print("=" * 80)
        
        query = (
            f"Parse the following Google Doc content and extract data sources for company {self.state.company_name}.\n\n"
            f"Raw content:\n{raw_data_sources}\n\n"
            f"Extract and organize the data sources into the required structure.\n"
        )
        
        result = await organizer_agent.kickoff_async(query, response_format=DataSources)
        # extract_structured_output returns DataSources instance when target_schema is provided
        return extract_structured_output(result, DataSources)  # type: ignore


    @listen(get_data_sources)
    async def parse_data_sources(self, data_sources: DataSources) -> Dict[str, str]:
        """Parse individual data sources and return markdown content for each"""
        if self.state.skip_method and self.state.parsed_data_sources:
            return self.state.parsed_data_sources
        
        print("Data sources to parse:", data_sources)
        
        parsed_sources = {}
        
        # Helper function to process any source
        async def process_source(source_name: str, raw_content: str) -> str:
            query = (
                f"Clean and organize the following content into well-structured markdown in human readable format.\n\n"
                f"Source: {source_name}\n"
                f"Raw content:\n{raw_content}\n\n"
                f"Return clean, well-formatted markdown content."
            )
            result = await organizer_agent.kickoff_async(query)
            return clean_markdown_output(result.raw if hasattr(result, 'raw') else str(result))
        
        # Process Google Docs
        if data_sources.google_docs:
            print(f"📄 Processing {len(data_sources.google_docs)} Google Doc(s)...")
            google_doc_processor = GoogleDocProcessor()
            for i, doc_url in enumerate(data_sources.google_docs):
                print(f"  📄 Processing Google Doc {i+1}/{len(data_sources.google_docs)}: {doc_url}")
                raw_content = google_doc_processor._run(doc_url).strip()
                parsed_sources[f"Google Doc {i+1}"] = await process_source(f"Google Doc {i+1}", raw_content)
                print(f"  ✅ Google Doc {i+1} processed ({len(raw_content)} chars)")
        else:
            print("📄 No Google Docs to process")
        
        # Process Websites
        if data_sources.websites:
            print(f"🌐 Processing {len(data_sources.websites)} website(s)...")
            from src.diligence_agent.tools.cached_serper_tools import cached_serper_scraper
            for i, website_url in enumerate(data_sources.websites):
                print(f"  🌐 Processing website {i+1}/{len(data_sources.websites)}: {website_url}")
                raw_content = cached_serper_scraper._run(url=website_url)
                parsed_sources[f"Website: {website_url}"] = await process_source(f"Website: {website_url}", raw_content)
                print(f"  ✅ Website {i+1} processed ({len(raw_content)} chars)")
        else:
            print("🌐 No websites to process")
        
        # Process Slack Channels
        if data_sources.slack_channels:
            print(f"💬 Processing {len(data_sources.slack_channels)} Slack channel(s)...")
            for i, channel_id in enumerate(data_sources.slack_channels):
                print(f"  💬 Processing Slack channel {i+1}/{len(data_sources.slack_channels)}: {channel_id}")
                # Create channel dict with minimal info for fetch_slack_channel_data
                channel_info = {"id": channel_id, "name": channel_id, "description": ""}
                raw_content = fetch_slack_channel_data([channel_info])
                parsed_sources[f"Slack: {channel_id}"] = await process_source(f"Slack: {channel_id}", raw_content)
                print(f"  ✅ Slack channel {i+1} processed ({len(raw_content)} chars)")
        else:
            print("💬 No Slack channels to process")
        
        # Update state and write parsed data sources to files
        self.state.parsed_data_sources = parsed_sources
        write_parsed_data_sources(parsed_sources, self.state.company_name, self.state.current_date)
        return parsed_sources



    @listen(parse_data_sources)
    async def run_research_flows(self, parsed_data_sources: Dict[str, str]) -> ReportStructure:

        #if self.state.skip_method and self.state.report_structure:
        #    return self.state.report_structure
        
        # Define common inputs for all research flows
        base_inputs = {
            "company": self.state.company_name,
            "parsed_data_sources": parsed_data_sources,
            "current_date": self.state.current_date,
            "num_search_terms": self.state.num_search_terms,
            "num_websites": self.state.num_websites,
        }

        # Define research sections to execute
        research_sections = [
            "Company Overview",            
            "Product",
            "Competitive Landscape",
            "Market", 
            "Founders",
        ]

        # Execute subflows and map results using centralized function
        await execute_subflows_and_map_results(
            ResearchFlow,
            research_sections,
            base_inputs,
            self.state.report_structure,
            self.state.company_name,
            self.state.current_date,
            self.state.batch_size,
            self.state.batch_delay
        )

        print(f"✅ Research flows completed")
        return self.state.report_structure
    
    @listen(run_research_flows)
    async def run_non_research_flows(self) -> ReportStructure:
        """Write remaining sections of the report that are not covered by research flows"""
        #if self.state.skip_method and report_structure.company_overview_section and report_structure.why_interesting_section and report_structure.report_conclusion_section:
        #    return report_structure
        
         # Define common inputs for all research flows
        base_inputs = {
            "company": self.state.company_name,
            "report_structure": self.state.report_structure,
        }

        # Define research sections to execute
        non_research_sections = [
            "Company Overview",            
            "Why Interesting",
            "Report Conclusion",
        ]
        
        # Execute subflows and map results using centralized function
        await execute_subflows_and_map_results(
            NonResearchFlow,
            non_research_sections,
            base_inputs,
            self.state.report_structure,
            self.state.company_name,
            self.state.current_date,
            self.state.batch_size,
            self.state.batch_delay
        )

        print(f"✅ Non-research flows completed")
        return self.state.report_structure
    
    @listen(run_non_research_flows)
    async def finalize_report(self, report_structure: ReportStructure) -> str:
        """Finalize and format the complete report"""
        query = (
            f"You are given the following structured report about company {self.state.company_name}:\n\n"
            f"{report_structure}\n\n"
            f"Using this data, write a comprehensive and well-structured investment report.\n\n"
            f"Ensure clarity and coherence in your writing. Eliminate redundancies and ensure a smooth flow between sections.\n\n"
            f"Be thorough and don't omit any details.\n\n"
            f"Return an output in Markdown format."
        )

        result = await writer_agent.kickoff_async(query)
        raw_final_report = result.raw if hasattr(result, 'raw') else str(result)
        final_report = clean_markdown_output(raw_final_report)
        
        # Save final report using unified file writing function
        if final_report:
            final_report_filepath = write_section_file("Final Report", final_report, self.state.company_name, self.state.current_date)
            if final_report_filepath:
                print(f"✅ Final report completed")
        
        return final_report


async def kickoff(clear_cache: bool = False) -> Any:
    # Clear cache if requested
    if clear_cache:
        from src.diligence_agent.tools.cached_serper_tools import cached_serper_search, cached_serper_scraper
        cached_serper_search.clear_cache()
        cached_serper_scraper.clear_cache()
        print("🗑️ Cache cleared")
    
    diligence_flow = DiligenceFlow()
    result = await diligence_flow.kickoff_async(
        inputs={
            "company_name": "tensorstax",
            "current_date": datetime.now().strftime("%Y-%m-%d"),
            "skip_method": False
        }
    )
    flow_id = getattr(diligence_flow.state, 'id', 'unknown')
    print(f"🆔 Flow completed! To run individual tasks, use this ID: {flow_id}")
    
    # Show cache performance stats
    from src.diligence_agent.tools.cached_serper_tools import print_cache_stats
    print_cache_stats()
    
    return result


async def kickoff_task(flow_id: Optional[str] = None, clear_cache: bool = False) -> Any:
    """Run a single task of the flow with persistent state."""
    # Clear cache if requested
    if clear_cache:
        from src.diligence_agent.tools.cached_serper_tools import cached_serper_search, cached_serper_scraper
        cached_serper_search.clear_cache()
        cached_serper_scraper.clear_cache()
        print("🗑️ Cache cleared")

    diligence_flow = DiligenceFlow()

    if flow_id:
        # Load existing flow state using the provided ID
        result = await diligence_flow.kickoff_async(
            inputs={"id": flow_id, "skip_method": True}
        )
    else:
        # No flow ID provided, start fresh with skip_method=True
        result = await diligence_flow.kickoff_async(
            inputs={"company_name": "tensorstax", "current_date": datetime.now().strftime("%Y-%m-%d"), "skip_method": True}
        )

    flow_id = getattr(diligence_flow.state, 'id', 'unknown')
    print(f"✅ Task completed using flow ID: {flow_id}")
    return result


def plot():
    # Ensure task_outputs directory exists
    os.makedirs("task_outputs", exist_ok=True)

    diligence_flow = DiligenceFlow()
    diligence_flow.plot("task_outputs/DiligenceFlowPlot")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Run with flow ID if provided
        flow_id = sys.argv[1]
        asyncio.run(kickoff_task(flow_id))
    else:
        # Run full flow by default
        asyncio.run(kickoff())

    plot()


