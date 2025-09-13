from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from crewai.flow.flow import Flow, listen, start
from crewai.flow.persistence import persist
from datetime import datetime
from diligence_agent.tools.google_doc_processor import GoogleDocProcessor
import asyncio
from diligence_agent.schemas import ReportStructure, DataSources, CompanyDataSources
from diligence_agent.research_flow import ResearchFlow
from diligence_agent.non_research_flow import NonResearchFlow
from diligence_agent.agents import organizer_agent, writer_agent
from diligence_agent.utils import (
    execute_subflows_and_map_results,
    extract_structured_output,
    fetch_slack_channel_data,
    write_section_file,
    clean_markdown_output,
    write_parsed_data_sources,
    write_final_report_to_google_doc
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
    batch_size: int = 1
    batch_delay: float = 0.0  # seconds
    num_search_terms: int = 1
    num_websites: int = 1

    # section control - list of sections to run
    sections_to_run: List[str] = [
        "Get Data Sources",
        "Parse Data Sources", 
        "Company Overview",            
        "Product",
        "Competitive Landscape",
        "Market", 
        "Founders",
        "Why Interesting",
        "Report Conclusion",
        "Final Report"
    ]

    # data sources organizer flow
    data_sources_file: str = ""
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
        """Parse Google Doc containing data sources and extract company name"""
        if "Get Data Sources" not in self.state.sections_to_run:
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
            f"Parse the following Google Doc content and extract both the company name and data sources.\n\n"
            f"Raw content:\n{raw_data_sources}\n\n"
            f"Extract:\n"
            f"1. The company name (look for patterns like 'Company name: X' or similar)\n"
            f"2. All data sources organized into the required structure\n\n"
            f"Return both the company name and structured data sources."
        )
        
        result = await organizer_agent.kickoff_async(query, response_format=CompanyDataSources)
        company_data_sources = extract_structured_output(result, CompanyDataSources)  # type: ignore
        
        # Extract and store company name in state
        if company_data_sources.company_name:
            self.state.company_name = company_data_sources.company_name.strip()
            print(f"📋 Extracted company name: {self.state.company_name}")
        else:
            raise ValueError("Could not extract company name from the data sources document. Please ensure the document contains 'Company name: [Name]' or similar.")
        
        # Extract and store data sources in state (only the DataSources part)
        self.state.data_sources = company_data_sources.data_sources
        
        # Return only the DataSources for the flow
        return self.state.data_sources


    @listen(get_data_sources)
    async def parse_data_sources(self, data_sources: DataSources) -> Dict[str, str]:
        """Parse individual data sources and return markdown content for each"""
        if "Parse Data Sources" not in self.state.sections_to_run:
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
            from diligence_agent.tools.cached_serper_tools import cached_serper_scraper
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
        
        # Define research sections to run
        research_sections = ["Company Overview", "Product", "Competitive Landscape", "Market", "Founders"]
        sections_to_execute = [s for s in research_sections if s in self.state.sections_to_run]
        
        if not sections_to_execute:
            print("⏭️  Skipping research flows (no research sections requested)")
            # Still need to return existing report structure from state
            return self.state.report_structure
        
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
            sections_to_execute,
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
        
        # Define non-research sections to run
        non_research_sections = ["Why Interesting", "Report Conclusion"]
        sections_to_execute = [s for s in non_research_sections if s in self.state.sections_to_run]
        
        if not sections_to_execute:
            print("⏭️  Skipping non-research flows (no non-research sections requested)")
            return self.state.report_structure
        
        # Define common inputs for all non-research flows
        base_inputs = {
            "company": self.state.company_name,
            "report_structure": self.state.report_structure,
        }

        # Execute subflows and map results using centralized function
        await execute_subflows_and_map_results(
            NonResearchFlow,
            sections_to_execute,
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
        # Skip finalization if Final Report is not in sections to run
        if "Final Report" not in self.state.sections_to_run:
            print("⏭️  Skipping report finalization (Final Report not requested)")
            return self.state.final_report
        
        query = (
            f"You are given the following structured report about company {self.state.company_name}:\n\n"
            f"{report_structure}\n\n"
            f"Using this data, write a comprehensive and well-structured investment report.\n\n"
            f"Ensure clarity and coherence in your writing. Eliminate redundancies and ensure a smooth flow between sections.\n\n"
            f"Be thorough and don't omit any details.\n\n"
            f"Return an output in pure Markdown format without any additional thoughts or comments."
        )
        
        result = await writer_agent.kickoff_async(query)
        raw_final_report = result.raw if hasattr(result, 'raw') else str(result)
        final_report = clean_markdown_output(raw_final_report)
        
        # Save final report using unified file writing function
        if final_report:
            final_report_filepath = write_section_file("Final Report", final_report, self.state.company_name, self.state.current_date)
            if final_report_filepath:
                print(f"✅ Final report completed")
            
            # Also write to Google Drive
            document_name = f"{self.state.company_name}_Final_Report"
            google_doc_url = write_final_report_to_google_doc(
                document_name=document_name,
                markdown_content=final_report,
                source_doc_url=self.state.data_sources_file
            )
            
            if google_doc_url:
                print(f"🔗 Google Doc available at: {google_doc_url}")
        
        self.state.final_report = final_report
        return self.state.final_report


async def kickoff(data_sources_file: Optional[str] = None, flow_id: Optional[str] = None, sections: Optional[List[str]] = None, clear_cache: bool = False, num_search_terms: int = 5, num_websites: int = 10) -> Any:
    """
    Run the diligence flow with optional flow ID and specific sections.
    
    Args:
        data_sources_file: Google Doc URL containing company data sources (required for new flows)
        flow_id: Optional flow ID to resume existing flow
        sections: Optional list of specific sections to run
        clear_cache: Whether to clear the cache before running
    """
    # Clear cache if requested
    if clear_cache:
        from diligence_agent.tools.cached_serper_tools import cached_serper_search, cached_serper_scraper
        cached_serper_search.clear_cache()
        cached_serper_scraper.clear_cache()
        print("🗑️ Cache cleared")
    
    diligence_flow = DiligenceFlow()
    
    # Prepare inputs
    if flow_id:
        # Resuming existing flow
        inputs = {"id": flow_id}
        print(f"🔄 Resuming existing flow: {flow_id}")
        
        # Override sections if specified
        if sections:
            print(f"🎯 Running specific sections: {sections}")
            inputs["sections_to_run"] = sections # type: ignore
            print(f"📋 Sections to run: {sections}")
    else:
        # No flow ID provided, start fresh
        if not data_sources_file:
            raise ValueError("data_sources_file is required for new flows. Please provide a Google Doc URL containing company data sources.")
        
        inputs = {
            "data_sources_file": data_sources_file,
            "current_date": datetime.now().strftime("%Y-%m-%d"),
            "num_search_terms": num_search_terms,
            "num_websites": num_websites,
        }
        print(f"📄 Starting new flow with data sources: {data_sources_file}")
        
        # Override sections if specified for new flows
        if sections:
            print(f"🎯 Running specific sections: {sections}")
            inputs["sections_to_run"] = sections # type: ignore
    
    result = await diligence_flow.kickoff_async(inputs=inputs)
    flow_id = getattr(diligence_flow.state, 'id', 'unknown')
    
    if sections:
        print(f"✅ Sections completed using flow ID: {flow_id}")
    else:
        print(f"🆔 Flow completed! To run individual tasks, use this ID: {flow_id}")
    
    # Show cache performance stats
    try:
        from diligence_agent.tools.cached_serper_tools import print_cache_stats
        print_cache_stats()
    except Exception as e:
        print(f"❌ Error showing cache stats: {e}")
        import traceback
        traceback.print_exc()
    
    return result


def plot():
    # Ensure task_outputs directory exists
    os.makedirs("task_outputs", exist_ok=True)

    diligence_flow = DiligenceFlow()
    diligence_flow.plot("task_outputs/DiligenceFlowPlot")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Run Diligence Agent flow-based analysis')
    parser.add_argument('--sources', type=str, help='Google Doc URL containing company data sources (required for new flows)')
    parser.add_argument('--flow_id', type=str, help='Flow ID to resume existing flow')
    parser.add_argument('--sections', type=str, help='Comma-separated list of sections to run (e.g., "Final Report,Market")')
    parser.add_argument('--clear_cache', action='store_true', help='Clear search/scraping cache before running')
    parser.add_argument('--search_terms', type=int, default=5, help='Number of search terms to generate for research (default: 5)')
    parser.add_argument('--websites', type=int, default=10, help='Number of websites to scrape per search (default: 10)')
    
    args = parser.parse_args()
    
    # Parse sections if provided
    sections = None
    if args.sections:
        sections = [s.strip() for s in args.sections.split(',')]
    
    # Run the flow with parsed arguments
    try:
        asyncio.run(kickoff(
            data_sources_file=args.sources,
            flow_id=args.flow_id, 
            sections=sections,
            clear_cache=args.clear_cache,
            num_search_terms=args.search_terms,
            num_websites=args.websites
        ))
        plot()
    except ValueError as e:
        print(f"❌ Error: {e}")
        print("💡 Use --help for usage information")
        exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


