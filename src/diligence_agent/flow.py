from pydantic import BaseModel
from crewai.flow.flow import Flow, listen, start, router, or_
from crewai.flow.persistence import persist
from crewai_tools import SerperDevTool, SerperScrapeWebsiteTool
from crewai import Agent
from crewai.llm import LLM
from pydantic import BaseModel, Field
from datetime import datetime
from src.diligence_agent.tools.google_doc_processor import GoogleDocProcessor

from src.diligence_agent.workflow import validate_json_output
from src.diligence_agent.mcp_config import get_slack_tools
import asyncio
import json
from opik.integrations.crewai import track_crewai
track_crewai(project_name="diligence-agent")

#model = "gpt-4o-mini"
#model = "gpt-4.1-mini"
model = "gemini/gemini-2.0-flash"

import os

llm = LLM(
    model=model,
    api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.0,
)

class OrganizerFeedback(BaseModel):
    feedback: str = Field(..., description="Feedback on the data quality and completeness")
    is_acceptable: bool = Field(..., description="Whether the organized data is acceptable or needs re-processing (True or False)")

class OrganizedData(BaseModel):
    data: dict = Field(..., description="Organized company data in structured JSON format")

class DiligenceState(BaseModel):
    # general info
    company_name: str = ""
    current_date: str = ""
    skip_method: bool = False
    
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
    goal="Search the web for valuable information about a topic.",
    backstory="You are an excellent researcher, who can search and browse the web to find thorough information about any topic.",
    verbose=True,
    llm=llm,
    max_iter=8,
    tools=[SerperDevTool()]
)

@persist()
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
        
        # Parse the raw JSON output
        raw_output = result.raw if hasattr(result, 'raw') else str(result)
        is_valid, cleaned_json = validate_json_output(raw_output)
        
        if is_valid:
            try:
                parsed_data = json.loads(cleaned_json)
                clean_questionnaire_data = parsed_data.get('data', parsed_data)  # Try root level if 'data' doesn't exist
            except (json.JSONDecodeError, KeyError):
                clean_questionnaire_data = {}
        else:
            clean_questionnaire_data = {}
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
        
        # Parse the raw JSON output
        raw_output = result.raw if hasattr(result, 'raw') else str(result)
        is_valid, cleaned_json = validate_json_output(raw_output)
        
        if is_valid:
            try:
                parsed_feedback = json.loads(cleaned_json)
                feedback = OrganizerFeedback(
                    feedback=parsed_feedback.get('feedback', 'Error parsing feedback'),
                    is_acceptable=parsed_feedback.get('is_acceptable', False)
                )
            except (json.JSONDecodeError, ValueError):
                feedback = OrganizerFeedback(feedback="Error parsing feedback JSON", is_acceptable=False)
        else:
            feedback = OrganizerFeedback(feedback="Error getting feedback - invalid JSON", is_acceptable=False)
            
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
    async def organize_slack_data(self, raw_slack_content: str) -> dict:
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
    async def generate_keywords(self):
        query = (
            f"Provide a list of 6 search terms that could be relevant in researching the background of the founders of company {self.state.company_name}.\n\n"
            f"To support your work, you have access to the following information about {self.state.company_name}:\n\n"
            f"{self.state.clean_questionnaire_content}\n\n"
            f"{self.state.clean_slack_content}\n\n"
            f"You also have the ability to search the web to verify who the founders are or gather any additional information."
        )
        query = (
            f"Perform a thorough research on the background of the founders of company {self.state.company_name} by following these steps:\n\n"
            f"1. Search the web to confirm who the founders are.\n\n"
            f"2. List 6 search terms that would help evaluate their background, their trustworthiness, and potential as startup executives.\n\n"
            f"3. Perform searches for each of these terms, then compile a list of the top 10 most relevant websites.\n\n"
            f"To support your research, you have access to the following information:\n\n"
            f"{self.state.clean_questionnaire_content}\n\n"
            f"{self.state.clean_slack_content}\n\n"
        )
        query = (
            f"Provide detailed plan for researching the background of the founders of company {self.state.company_name} "
            f"and understand their ability to lead a company successfully in this space. "
            f"This plan will be used by investors to conduct a thorough online web research on whether to invest in this company. "
            f"To support your work, you have access to the following information about {self.state.company_name}:\n\n"
            f"{self.state.clean_questionnaire_content}\n\n"
            f"{self.state.clean_slack_content}\n\n"
            f"You also have the ability to search the web to verify who the founders are or gather any additional information."
        )
        result = await researcher_agent.kickoff_async(query)
        print("Generate keywords result:", result)
        return result.raw


async def kickoff():
    diligence_flow = DiligenceFlow()
    result = await diligence_flow.kickoff_async(
        inputs={"company_name": "tensorstax", "current_date": datetime.now().strftime("%Y-%m-%d"), "skip_method": False}
    )
    print("State: ", diligence_flow.state)
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
    
    print("Updated State: ", diligence_flow.state)
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


