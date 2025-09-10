from pydantic import BaseModel
from typing import Dict, Any, Optional
from crewai.flow.flow import Flow, listen, start
from crewai.flow.persistence import persist
from crewai import Agent
from crewai.llm import LLM
from datetime import datetime
from src.diligence_agent.tools.google_doc_processor import GoogleDocProcessor
import asyncio
from src.diligence_agent.research_flow import ResearchFlow
from src.diligence_agent.schemas import ReportStructure
from src.diligence_agent.utils import execute_coroutines, extract_structured_output, fetch_slack_channel_data
from opik.integrations.crewai import track_crewai
track_crewai(project_name="diligence-agent")


#model = "gpt-4o-mini"
model = "gpt-4.1-mini"
#model = "gpt-5-nano"
#model = "gemini/gemini-1.5-flash"
#model = "gemini/gemini-2.0-flash"
#model = "gemini/gemini-2.5-flash"

import os

llm = LLM(
    model=model,
    #api_key=os.getenv("GOOGLE_API_KEY"),
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.0,
)


class DiligenceState(BaseModel):
    # general info
    company_name: str = ""
    current_date: str = ""
    skip_method: bool = False
    parallel_execution: bool = False  # Toggle for parallel vs sequential execution

    # questionnaire organizer flow
    questionaire_url: str = "https://docs.google.com/spreadsheets/d/1ySCoSgVf2A00HD8jiCEV-EYADuYJP3P2Ewwx_DqARDg/edit?usp=sharing"
    raw_questionnaire_content: str = ""
    clean_questionnaire_content: dict = {}
    raw_slack_content: str = ""
    clean_slack_content: str = ""

    # research report structure
    report_structure: ReportStructure = ReportStructure()

    # slack organizer flow
    slack_channels: list = [{"name": "diligence_tensorstax", "id":"C09AE80U8C8","description": "Dedicated channel for TensorStax due diligence discussions."},
                            {"name": "q32025", "id": "C09750Z9HQ8", "description": "Channel for group discussions about companies, including TensorStax."},]

organizer_agent = Agent(
    role="Data organizer",
    goal="Organize unstructured data into a clean format.",
    backstory="You are an excellent data organizer with strong attention to detail.",
    verbose=True,
    llm=llm,
    max_iter=8,
)


@persist(verbose=True)
class DiligenceFlow(Flow[DiligenceState]):

    @start()
    def retrieve_questionnaire_data(self) -> str:
        """Fetch Google Docs content upfront to reduce costs and increase reliability"""
        if self.state.skip_method and self.state.raw_questionnaire_content:
            return self.state.raw_questionnaire_content

        google_doc_processor = GoogleDocProcessor()
        raw_questionnaire_content = google_doc_processor._run(self.state.questionaire_url).strip()
        self.state.raw_questionnaire_content = raw_questionnaire_content
        return raw_questionnaire_content

    @listen(retrieve_questionnaire_data)
    async def organize_questionnaire_data(self) -> Dict[str, Any]:
        """Create a Google Doc processing task with optional feedback"""
        if self.state.skip_method and self.state.clean_questionnaire_content:
            return self.state.clean_questionnaire_content

        query = (
            f"Process and extract data from Google Docs about company {self.state.company_name}.\n"
            f"Below is the raw content from the Google Docs:\n\n"
            f"{self.state.raw_questionnaire_content}\n\n"
            f"Current date: {self.state.current_date}\n"
            f"Organize this data into a structured JSON format by question and answer. Be thorough and include all relevant details.\n"
        )
        result = await organizer_agent.kickoff_async(query)
        extracted_data = extract_structured_output(result)
        self.state.clean_questionnaire_content = extracted_data if isinstance(extracted_data, dict) else {}
        return self.state.clean_questionnaire_content

    @listen(organize_questionnaire_data)
    async def retrieve_slack_data(self) -> str:
        """Fetch Slack content using MCP tools"""
        if self.state.skip_method and self.state.raw_slack_content:
            return self.state.raw_slack_content

        self.state.raw_slack_content = fetch_slack_channel_data(self.state.slack_channels)
        return self.state.raw_slack_content

    @listen(retrieve_slack_data)
    async def organize_slack_data(self, raw_slack_content: str) -> str:
        """Organize Slack data"""
        if self.state.skip_method and self.state.clean_slack_content:
            return self.state.clean_slack_content

        query = (
            f"Process and extract data from Slack channels about company {self.state.company_name}.\n"
            f"Below is the raw content from Slack:\n\n"
            f"{raw_slack_content}\n\n"
            f"Current date: {self.state.current_date}\n"
            f"Organize this data into a human readable markdown format. Be thorough and include all relevant details about this company.\n"
        )
        result = await organizer_agent.kickoff_async(query)
        # Extract string content from agent result
        clean_slack_data = result.raw if hasattr(result, 'raw') else str(result)
        self.state.clean_slack_content = clean_slack_data
        return clean_slack_data

    @listen(organize_slack_data)
    async def run_research_flows(self) -> ReportStructure:
        # Define common inputs for all research flows
        base_inputs = {
            "company": self.state.company_name,
            "questionnaire_data": self.state.clean_questionnaire_content,
            "slack_data": self.state.clean_slack_content,
            "current_date": self.state.current_date,
            "num_search_terms": 3,
            "num_websites": 5,
        }

        # Define research sections and their corresponding schema fields
        research_sections = [
            
            ("Product", "product_section"),
            #("Competitive Landscape", "competitive_landscape_section"),
            #("Market", "market_section"),
            #("Founders", "founders_section"),
        ]

        # Create coroutines for all research flows
        coroutines = []
        for section_name, _ in research_sections:
            subflow = ResearchFlow()
            coroutines.append(subflow.kickoff_async(
                inputs={
                    **base_inputs,
                    "section": section_name,
                }
            ))

        # Execute using our central utility function with unified tracing
        results = await execute_coroutines(coroutines, parallel=self.state.parallel_execution)

        # Map research results to appropriate report structure fields
        for i, (section_name, field_name) in enumerate(research_sections):
            if i < len(results):
                # Extract markdown content from result
                markdown_content = str(results[i]) if results[i] else ""
                # Set the appropriate field in report structure
                setattr(self.state.report_structure, field_name, markdown_content)
                print(f"✅ {section_name} research completed and added to report")

        print(f"🎉 All research flows completed! Report structure populated.")
        return self.state.report_structure



async def kickoff(parallel_execution: bool = True) -> Any:
    diligence_flow = DiligenceFlow()
    result = await diligence_flow.kickoff_async(
        inputs={
            "company_name": "tensorstax",
            "current_date": datetime.now().strftime("%Y-%m-%d"),
            "skip_method": False,
            "parallel_execution": parallel_execution
        }
    )
    flow_id = getattr(diligence_flow.state, 'id', 'unknown')
    print(f"🆔 Flow completed! To run individual tasks, use this ID: {flow_id}")
    return result


async def kickoff_task(flow_id: Optional[str] = None) -> Any:
    """Run a single task of the flow with persistent state."""

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


