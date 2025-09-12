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
    
    # execution parameters
    batch_size: int = 2
    batch_delay: float = 0.0  # seconds
    num_search_terms: int = 5
    num_websites: int = 10

    # section control
    research_sections: List[str] = [
        "Company Overview",            
        "Product",
        "Competitive Landscape",
        "Market", 
        "Founders",
    ]
    non_research_sections: List[str] = [         
        "Why Interesting",
        "Report Conclusion",
    ]
    data_processing_steps: List[str] = [
        "Get Data Sources",
        "Parse Data Sources",
    ]

    # data sources organizer flow
    data_sources_file: str = "https://docs.google.com/document/d/1TZEg-gljazGMUuG1KWKoNc3PDHMGLahD5ofd1BoBWR8/edit?usp=sharing"
    data_sources: DataSources = DataSources(
        google_docs=[],
        pdfs=[],
        websites=[],
        slack_channels=[]
    )
    parsed_data_sources: Dict[str, str] = {}
    
    # Report structure
    report_structure: ReportStructure = ReportStructure(
        company_overview_section="",
        product_section="",
        why_interesting_section="",
        founders_section="",
        competitive_landscape_section="",
        market_section="",
        report_conclusion_section=""
    )

    final_report: str = ""

    

@persist(verbose=True)
class DiligenceFlow(Flow[DiligenceState]):

    @start()
    async def get_data_sources(self) -> DataSources:
        """Parse Google Doc containing data sources and return structured DataSources schema"""
        if "Get Data Sources" not in self.state.data_processing_steps:
            print("⏭️  Skipping data source extraction")
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
        if "Parse Data Sources" not in self.state.data_processing_steps:
            print("⏭️  Skipping data source parsing")
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
        
        # Process Websites
        if data_sources.websites:
            print(f"🌐 Processing {len(data_sources.websites)} website(s)...")
            from src.diligence_agent.tools.cached_serper_tools import cached_serper_scraper
            for i, website_url in enumerate(data_sources.websites):
                print(f"  🌐 Processing website {i+1}/{len(data_sources.websites)}: {website_url}")
                raw_content = cached_serper_scraper._run(url=website_url)
                parsed_sources[f"Website: {website_url}"] = await process_source(f"Website: {website_url}", raw_content)
                print(f"  ✅ Website {i+1} processed ({len(raw_content)} chars)")
        
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
        
        # Update state and write parsed data sources to files
        self.state.parsed_data_sources = parsed_sources
        write_parsed_data_sources(parsed_sources, self.state.company_name, self.state.current_date)
        return parsed_sources



    @listen(parse_data_sources)
    async def run_research_flows(self, parsed_data_sources: Dict[str, str]) -> ReportStructure:
        """Execute research flows to generate report sections that require external research"""
        
        # Define common inputs for all research flows
        base_inputs = {
            "company": self.state.company_name,
            "parsed_data_sources": parsed_data_sources,
            "current_date": self.state.current_date,
            "num_search_terms": self.state.num_search_terms,
            "num_websites": self.state.num_websites,
        }

        # Execute subflows and map results using centralized function
        await execute_subflows_and_map_results(
            ResearchFlow,
            self.state.research_sections,
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
        
        # Define common inputs for all research flows
        base_inputs = {
            "company": self.state.company_name,
            "report_structure": self.state.report_structure,
        }

        # Execute subflows and map results using centralized function
        await execute_subflows_and_map_results(
            NonResearchFlow,
            self.state.non_research_sections,
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
        # Skip finalization if running specific sections (not a full report)
        if not (self.state.research_sections and self.state.non_research_sections):
            print("⏭️  Skipping report finalization (running specific sections only)")
            return self.state.final_report
        
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
        self.state.final_report = final_report
        return self.state.final_report


async def kickoff(flow_id: Optional[str] = None, sections: Optional[List[str]] = None, clear_cache: bool = False) -> Any:
    """
    Run the diligence flow with optional flow ID and specific sections.
    
    Args:
        flow_id: Optional flow ID to resume existing flow
        sections: Optional list of specific sections to run
        clear_cache: Whether to clear the cache before running
    """
    # Clear cache if requested
    if clear_cache:
        from src.diligence_agent.tools.cached_serper_tools import cached_serper_search, cached_serper_scraper
        cached_serper_search.clear_cache()
        cached_serper_scraper.clear_cache()
        print("🗑️ Cache cleared")
    
    diligence_flow = DiligenceFlow()
    
    # Prepare inputs
    if flow_id:
        inputs = {"id": flow_id}
        
        # Override section lists if sections are specified
        if sections:
            print(f"🎯 Running specific sections: {sections}")
            
            research_sections = {"Company Overview", "Product", "Competitive Landscape", "Market", "Founders"}
            non_research_sections = {"Why Interesting", "Report Conclusion"}
            data_processing_steps = {"Get Data Sources", "Parse Data Sources"}
            
            specified_research = [s for s in sections if s in research_sections]
            specified_non_research = [s for s in sections if s in non_research_sections]
            specified_data_steps = [s for s in sections if s in data_processing_steps]
            
            # Set empty lists for sections not requested
            inputs["research_sections"] = specified_research if specified_research else []
            inputs["non_research_sections"] = specified_non_research if specified_non_research else []
            inputs["data_processing_steps"] = specified_data_steps if specified_data_steps else []
            
            print(f"📄 Data processing steps to run: {specified_data_steps}")
            print(f"📊 Research sections to run: {specified_research}")
            print(f"📝 Non-research sections to run: {specified_non_research}")
    else:
        # No flow ID provided, start fresh
        inputs = {
            "company_name": "tensorstax",
            "current_date": datetime.now().strftime("%Y-%m-%d"),
        }
    
    result = await diligence_flow.kickoff_async(inputs=inputs)
    flow_id = getattr(diligence_flow.state, 'id', 'unknown')
    
    if sections:
        print(f"✅ Sections completed using flow ID: {flow_id}")
    else:
        print(f"🆔 Flow completed! To run individual tasks, use this ID: {flow_id}")
    
    # Show cache performance stats
    from src.diligence_agent.tools.cached_serper_tools import print_cache_stats
    print_cache_stats()
    
    return result


def plot():
    # Ensure task_outputs directory exists
    os.makedirs("task_outputs", exist_ok=True)

    diligence_flow = DiligenceFlow()
    diligence_flow.plot("task_outputs/DiligenceFlowPlot")

if __name__ == "__main__":
    import sys

    # Parse command line arguments
    flow_id = sys.argv[1] if len(sys.argv) > 1 else None
    sections = sys.argv[2:] if len(sys.argv) > 2 else None
    
    # Run the flow with parsed arguments
    asyncio.run(kickoff(flow_id=flow_id, sections=sections))

    plot()


