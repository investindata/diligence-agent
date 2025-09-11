from pydantic import BaseModel
from typing import Dict, Any, Optional
from crewai.flow.flow import Flow, listen, start
from crewai.flow.persistence import persist
from datetime import datetime
from src.diligence_agent.tools.google_doc_processor import GoogleDocProcessor
import asyncio
from src.diligence_agent.schemas import ReportStructure
from src.diligence_agent.research_flow import ResearchFlow
from src.diligence_agent.non_research_flow import NonResearchFlow
from src.diligence_agent.agents import organizer_agent, writer_agent
from src.diligence_agent.utils import (
    execute_subflows_and_map_results,
    extract_structured_output,
    fetch_slack_channel_data,
    write_section_file,
    clean_markdown_output)
import os

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

    # questionnaire organizer flow
    questionaire_url: str = "https://docs.google.com/spreadsheets/d/1ySCoSgVf2A00HD8jiCEV-EYADuYJP3P2Ewwx_DqARDg/edit?usp=sharing"
    questionnaire_data: dict = {}
    slack_data: str = ""

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

    # slack organizer flow
    slack_channels: list = [{"name": "diligence_tensorstax", "id":"C09AE80U8C8","description": "Dedicated channel for TensorStax due diligence discussions."},
                            {"name": "q32025", "id": "C09750Z9HQ8", "description": "Channel for group discussions about companies, including TensorStax."},]


@persist(verbose=True)
class DiligenceFlow(Flow[DiligenceState]):

    @start()
    async def organize_questionnaire_data(self) -> Dict[str, Any]:
        """Create a Google Doc processing task"""
        if self.state.skip_method and self.state.questionnaire_data:
            return self.state.questionnaire_data
        
        # retrieve raw content from Google Docs
        google_doc_processor = GoogleDocProcessor()
        raw_questionnaire_data = google_doc_processor._run(self.state.questionaire_url).strip()

        query = (
            f"Process and extract data from Google Docs about company {self.state.company_name}.\n"
            f"Below is the raw content from the Google Docs:\n\n"
            f"{raw_questionnaire_data}\n\n"
            f"Current date: {self.state.current_date}\n"
            f"Organize this data into a structured JSON format by question and answer. Be thorough and include all relevant details.\n"
        )
        result = await organizer_agent.kickoff_async(query)
        extracted_data = extract_structured_output(result)
        self.state.questionnaire_data = extracted_data if isinstance(extracted_data, dict) else {}
        return self.state.questionnaire_data

    @listen(organize_questionnaire_data)
    async def organize_slack_data(self) -> str:
        """Organize Slack data"""
        if self.state.skip_method and self.state.slack_data:
            return self.state.slack_data
        
        raw_slack_content = fetch_slack_channel_data(self.state.slack_channels)

        query = (
            f"Process and extract data from Slack channels about company {self.state.company_name}.\n"
            f"Below is the raw content from Slack:\n\n"
            f"{raw_slack_content}\n\n"
            f"Current date: {self.state.current_date}\n"
            f"Organize this data into a human readable markdown format. Be thorough and include all relevant details about this company.\n"
        )
        result = await organizer_agent.kickoff_async(query)
        # Extract string content from agent result
        self.state.slack_data = result.raw if hasattr(result, 'raw') else str(result)
        return self.state.slack_data

    @listen(organize_slack_data)
    async def run_research_flows(self) -> ReportStructure:

        #if self.state.skip_method and self.state.report_structure:
        #    return self.state.report_structure
        
        # Define common inputs for all research flows
        base_inputs = {
            "company": self.state.company_name,
            "questionnaire_data": self.state.questionnaire_data,
            "slack_data": self.state.slack_data,
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
    async def run_non_research_flows(self, report_structure: ReportStructure) -> ReportStructure:
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
            f"Ensure clarity and coherence in your writing. Eliminate redundancies and ensure a smooth flow between sections."
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


