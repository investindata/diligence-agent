from pydantic import BaseModel
from crewai.flow.flow import Flow, listen, start, router, or_
from crewai import Agent
from crewai.llm import LLM
from pydantic import BaseModel, Field
from datetime import datetime
from src.diligence_agent.tools.google_doc_processor import GoogleDocProcessor
from src.diligence_agent.workflow import validate_json_output
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
    api_key=os.getenv("GOOGLE_API_KEY")
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
    
    # organizer flow
    questionaire_url: str = "https://docs.google.com/spreadsheets/d/1ySCoSgVf2A00HD8jiCEV-EYADuYJP3P2Ewwx_DqARDg/edit?usp=sharing"
    organizer_iterations: int = 0
    max_organizer_iterations: int = 4
    organizer_feedback: OrganizerFeedback = OrganizerFeedback(feedback="", is_acceptable=False)
    raw_questionnaire_content: str = ""
    clean_questionnaire_content: dict = {}
    raw_slack_content: str = ""
    clean_slack_content: str = ""

organizer_agent = Agent(
    role="Data organizer",
    goal="Organize unstructured data into a clean json.",
    backstory="You are an excellent data organizer with strong attention to detail.",
    verbose=True,
    llm=llm,
    max_iter=8,
)

class DiligenceFlow(Flow[DiligenceState]):

    @start()
    def retrieve_questionnaire_data(self) -> str:
        """Fetch Google Docs content upfront to reduce costs and increase reliability"""
        google_doc_processor = GoogleDocProcessor()
        raw_questionnaire_content = google_doc_processor._run(self.state.questionaire_url).strip()
        self.state.raw_questionnaire_content = raw_questionnaire_content
        return raw_questionnaire_content

    @listen(or_("retrieve_questionnaire_data", "Repeat"))
    async def organize_questionnaire_data(self) -> dict:
        """Create a Google Doc processing task with optional feedback"""
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
    def finalize_data(self) -> dict:
        """Final step when data organization is complete"""
        print("🎉 Data organization completed!")
        print(f"Final iterations: {self.state.organizer_iterations}")
        print(f"Final feedback: {self.state.organizer_feedback.feedback}")
        return self.state.clean_questionnaire_content



async def kickoff():
    diligence_flow = DiligenceFlow()
    result = await diligence_flow.kickoff_async(
        inputs={"company_name": "tensorstax", "current_date": datetime.now().strftime("%Y-%m-%d")}
    )
    print("State: ", diligence_flow.state)
    return result

def plot():
    poem_flow = DiligenceFlow()
    poem_flow.plot("DiligenceFlowPlot")

if __name__ == "__main__":
    asyncio.run(kickoff())
    plot()


