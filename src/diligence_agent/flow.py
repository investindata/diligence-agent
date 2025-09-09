from pydantic import BaseModel
from typing import Type
from crewai.flow.flow import Flow, listen, start, router, or_
from crewai.flow.persistence import persist
from crewai_tools import SerperDevTool
from crewai import Agent
from crewai.llm import LLM
from datetime import datetime
from src.diligence_agent.tools.google_doc_processor import GoogleDocProcessor
from src.diligence_agent.schemas import OrganizerFeedback, FounderNames, Founder
from src.diligence_agent.output_formatter import extract_structured_output
from src.diligence_agent.mcp_config import get_slack_tools, get_playwright_tools_with_auth
from src.diligence_agent.tools.simple_auth_helper import SimpleLinkedInAuthTool
import asyncio
from src.diligence_agent.research_flow import ResearchFlow, ResearchState
from src.diligence_agent.schemas import Founder
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
    founder_names: FounderNames = FounderNames(names=[])
    founder_websites: str = ""
    founder_profiles: list[dict] = []

    # questionnaire organizer flow
    questionaire_url: str = "https://docs.google.com/spreadsheets/d/1ySCoSgVf2A00HD8jiCEV-EYADuYJP3P2Ewwx_DqARDg/edit?usp=sharing"
    organizer_iterations: int = 0
    max_organizer_iterations: int = 1
    organizer_feedback: OrganizerFeedback = OrganizerFeedback(feedback="", is_acceptable=False)
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

researcher_agent = Agent(
    role="Researcher",
    goal="Search and scrape the web for valuable information about a topic using both search engines and browser automation.",
    backstory="You are an excellent researcher who can search the web using Serper and directly navigate websites using Playwright for thorough information gathering. When LinkedIn requires authentication, you can pause and request manual login.",
    verbose=True,
    llm=llm,
    max_iter=25,
    #tools=[SerperDevTool(), SimpleLinkedInAuthTool()] + get_playwright_tools_with_auth()
    tools=[SimpleLinkedInAuthTool()] + get_playwright_tools_with_auth()
)

# research_helper_agent = Agent(
#     role="Research Helper",
#     goal="Search the web and retrieve the most relevant results for the task at hand.",
#     backstory="You are an excellent researcher who can search the web using Serper to search the web.",
#     verbose=True,
#     llm=llm,
#     max_iter=10,
#     tools=[SerperDevTool()]
# )

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

    @listen(or_("retrieve_questionnaire_data", "Repeat"))
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
        if self.state.organizer_iterations > 0:
            query += (
                f"Below is your previous output and the feedback received. Please use this to improve your response:\n"
                f"Previous Output:\n{self.state.clean_questionnaire_content}\n\n"
                f"Feedback:\n{self.state.organizer_feedback.feedback}\n\n"
            )
        result = await organizer_agent.kickoff_async(query)


        clean_questionnaire_data = extract_structured_output(result)
        self.state.clean_questionnaire_content = clean_questionnaire_data
        return clean_questionnaire_data

    @listen(organize_questionnaire_data)
    async def quality_check_organized_data(self, clean_questionnaire_data: dict) -> OrganizerFeedback:
        if self.state.skip_method and self.state.organizer_feedback.feedback:
            return self.state.organizer_feedback

        query = (
            f"Check the output quality of the data organizer against the raw google doc data for company {self.state.company_name}. "
            f"If the output is too summarized and is missing valuable information, return it to the organizer for re-processing.\n\n"
            f"Below is the raw Google Docs data:\n\n"
            f"{self.state.raw_questionnaire_content}\n\n"
            f"And below is the organized data:\n\n"
            f"{clean_questionnaire_data}\n\n"
            f"Be extremely thorough and call out any missing details that exist in the raw data but not in the data organizer's output. "
            f"Return your feedback in JSON format with 'feedback' (string) and 'is_acceptable' (boolean) fields."
        )
        result = await organizer_agent.kickoff_async(query)

        feedback = extract_structured_output(result, OrganizerFeedback)

        self.state.organizer_feedback = feedback
        self.state.organizer_iterations += 1
        print("Feedback: ", feedback)
        return feedback

    @router(quality_check_organized_data)
    def decide_next_step(self) -> str:
        """Router to decide whether to continue or loop back to organizer"""
        # Ensure feedback is boolean
        is_acceptable = self.state.organizer_feedback.is_acceptable
        if type(is_acceptable) is str:
            is_acceptable = is_acceptable.lower() == "true"

        # Check if feedback is acceptable OR we've hit max iterations
        if (is_acceptable or
            self.state.organizer_iterations >= self.state.max_organizer_iterations):
            return "Done"
        else:
            return "Repeat"

    @listen("Done")
    async def retrieve_slack_data(self) -> str:
        """Fetch Slack content using MCP tools"""
        if self.state.skip_method and self.state.raw_slack_content:
            return self.state.raw_slack_content

        all_slack_content = ""
        slack_tools = get_slack_tools()

        for channel in self.state.slack_channels:
            # Add channel header with name and description
            channel_header = f"\n# Channel: {channel['name']}\n"
            channel_header += f"Description: {channel['description']}\n"
            channel_header += f"Channel ID: {channel['id']}\n\n"

            channel_content = ""

            if slack_tools:
                try:
                    # Find the slack_get_channel_history tool specifically
                    history_tool = None
                    for tool in slack_tools:
                        if hasattr(tool, 'name') and tool.name == 'slack_get_channel_history':
                            history_tool = tool
                            break

                    if history_tool:
                        # Use the MCP tool to fetch channel messages with correct parameter format
                        result = history_tool._run(
                            channel_id=channel['id'],
                            limit=500
                        )
                        channel_content = f"Messages from {channel['name']}:\n{result}\n"
                    else:
                        channel_content = f"slack_get_channel_history tool not found for {channel['name']}\n"

                except Exception as e:
                    channel_content = f"Error fetching data from {channel['name']}: {str(e)}\n"
            else:
                channel_content = f"Slack MCP tools not available for {channel['name']}\n"

            # Concatenate channel info with content
            all_slack_content += channel_header + channel_content + "\n"

        self.state.raw_slack_content = all_slack_content
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
        result = await researcher_agent.kickoff_async(query, response_format=FounderNames)
        self.state.founder_names = extract_structured_output(result, FounderNames)
        print("Founder names:", self.state.founder_names)
        return self.state.founder_names

    @listen(get_founders_names)
    async def run_research_flows(self):
        # Run subflows in parallel
        subflows = []

        # Founders flow
        for name in self.state.founder_names.names:
            subflow = ResearchFlow()
            subflows.append(subflow.kickoff_async(
                inputs={
                    "founder": name,
                    "company": self.state.company_name,
                    "section": "Founders",
                }
            ))

        results = await asyncio.gather(*subflows)
        
        # Collect founder profiles from subflow results and convert to dictionaries for JSON serialization
        self.state.founder_profiles = []
        for result in results:
            if hasattr(result, 'model_dump'):
                # Convert Pydantic object to dict
                self.state.founder_profiles.append(result.model_dump())
            elif isinstance(result, dict):
                self.state.founder_profiles.append(result)
            else:
                # Fallback for other types
                self.state.founder_profiles.append(str(result))
        
        print("Founder profiles:", self.state.founder_profiles)
        return self.state.founder_profiles



    # @listen(get_founders_names)
    # async def research_helper(self, founder_names):
    #     if self.state.skip_method and self.state.founder_websites:
    #         return self.state.founder_websites

    #     # Generate schema description using helper function
    #     schema_description = get_schema_description(Founder)

    #     query = (
    #         f"Create a list of the 10 most relevant websites to support a web research on founder {founder_names.names[1]} from company {self.state.company_name}.\n\n"
    #         f"The websites should be a comprehensive collection covering the following topics needed in the research:\n"
    #         f"{schema_description}\n\n"
    #         f"Follow these steps:\n\n"
    #         f"1. Come up with a list of 5 relevant search terms.\n\n"
    #         f"2. Perform a search for each term.\n\n"
    #         f"3. Compile a list of the top 10 websites that will help gather information for all these data points."
    #     )
    #     result = await research_helper_agent.kickoff_async(query)
    #     self.state.founder_websites = result.raw
    #     print("Websites:", self.state.founder_websites)
    #     return self.state.founder_websites



    # @listen(research_helper)
    # async def research_founder(self):

    #     schema_description = get_schema_description(Founder)

    #     query = (
    #         f"Perform a thorough web research of founder {self.state.founder_names.names[1]} from company {self.state.company_name}.\n\n"
    #         f"You are given a list of relevant wesbites below:\n\n"
    #         f"{self.state.founder_websites}\n\n"
    #         f"Scrape each website and collect the necessary content to generate an output based on the provided structured output schema, covering:\n\n"
    #         f"{schema_description}\n\n"
    #     )

    #     result = await researcher_agent.kickoff_async(query, response_format=Founder)
    #     founder_info = extract_structured_output(result, Founder)
    #     print("Founder info:", founder_info)
    #     return founder_info



async def kickoff():
    diligence_flow = DiligenceFlow()
    result = await diligence_flow.kickoff_async(
        inputs={"company_name": "tensorstax", "current_date": datetime.now().strftime("%Y-%m-%d"), "skip_method": False}
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


