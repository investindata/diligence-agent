from pydantic import BaseModel
from typing import Type
from crewai.flow.flow import Flow, listen, start
from crewai.flow.persistence import persist
from crewai_tools import SerperDevTool
from crewai import Agent
from crewai.llm import LLM
from datetime import datetime
from src.diligence_agent.tools.google_doc_processor import GoogleDocProcessor
from src.diligence_agent.schemas import FounderNames
from src.diligence_agent.mcp_config import get_playwright_tools_with_auth
from src.diligence_agent.tools.simple_auth_helper import SimpleLinkedInAuthTool
import asyncio
from src.diligence_agent.research_flow import ResearchFlow, ResearchState
from src.diligence_agent.utils import execute_coroutines, extract_structured_output, make_json_serializable, fetch_slack_channel_data
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
    founder_names: FounderNames = FounderNames(names=[])
    founder_websites: str = ""
    founder_profiles: list[dict] = []

    # questionnaire organizer flow
    questionaire_url: str = "https://docs.google.com/spreadsheets/d/1ySCoSgVf2A00HD8jiCEV-EYADuYJP3P2Ewwx_DqARDg/edit?usp=sharing"
    organizer_iterations: int = 0
    max_organizer_iterations: int = 1
    raw_questionnaire_content: str = ""
    clean_questionnaire_content: dict = {}
    raw_slack_content: str = ""
    clean_slack_content: str = ""

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

get_founders_agent = Agent(
    role="",
    goal="Search the web for the founders names.",
    backstory="You are an excellent researcher who can search the web using Serper.",
    verbose=True,
    llm=llm,
    max_iter=1,
    tools=[SerperDevTool()]
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
    async def organize_questionnaire_data(self) -> dict:
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
        self.state.clean_questionnaire_content = extract_structured_output(result)
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
    async def get_founders_names(self):
        if self.state.skip_method and self.state.founder_names:
            return self.state.founder_names
        query = (
            f"Search the web for the names of the founders of company {self.state.company_name}. "
            f"Do NOT include any explanation, thought, or commentary. Only output JSON."
        )
        result = await get_founders_agent.kickoff_async(query, response_format=FounderNames)
        self.state.founder_names = extract_structured_output(result, FounderNames)
        print("Founder names:", self.state.founder_names)
        return self.state.founder_names

    @listen(get_founders_names)
    async def run_research_flows(self):
        # Create coroutines for all founder research tasks
        coroutines = []
        for name in self.state.founder_names.names:
            subflow = ResearchFlow()
            coroutines.append(subflow.kickoff_async(
                inputs={
                    "section": "Founders",
                    "section_instruction": f"Perform a thorough research on founder {name} of company {self.state.company_name}.\n\n",
                    "num_search_terms": 1, 
                    "num_websites": 1,     
                }
            ))
        
        # Create competitive landscape coroutine
        subflow = ResearchFlow()
        coroutines.append(subflow.kickoff_async(
            inputs={
                "section": "Competitive Landscape",
                "section_instruction": f"Perform a thorough research on the competitive landscape of company {self.state.company_name}.\n\n",
                "num_search_terms": 1, 
                "num_websites": 1,
            }
        ))

        # Create market coroutine
        subflow = ResearchFlow()
        coroutines.append(subflow.kickoff_async(
            inputs={
                "section": "Market",
                "section_instruction": f"Perform a thorough research on the market of company {self.state.company_name}.\n\n",
                "num_search_terms": 1, 
                "num_websites": 1,
            }
        ))

        # Execute using our central utility function with unified tracing
        results = await execute_coroutines(coroutines, parallel=self.state.parallel_execution)
        
        # Collect founder profiles from subflow results and make them JSON serializable
        self.state.founder_profiles = []
        for result in results:
            # Use utility function to handle all JSON serialization including HttpUrl
            serialized_result = make_json_serializable(result)
            self.state.founder_profiles.append(serialized_result)
        
        print("Founder profiles:", self.state.founder_profiles)
        return self.state.founder_profiles



async def kickoff(parallel_execution: bool = True):
    diligence_flow = DiligenceFlow()
    result = await diligence_flow.kickoff_async(
        inputs={
            "company_name": "tensorstax", 
            "current_date": datetime.now().strftime("%Y-%m-%d"), 
            "skip_method": False,
            "parallel_execution": parallel_execution
        }
    )
    print(f"🆔 Flow completed! To run individual tasks, use this ID: {diligence_flow.state.id}")
    return result


async def kickoff_task(flow_id: str = None):
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

    print(f"✅ Task completed using flow ID: {diligence_flow.state.id}")
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


