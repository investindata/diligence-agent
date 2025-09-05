from pydantic import BaseModel
from crewai.flow.flow import Flow, listen, start, router
from crewai.llm import LLM
from pydantic import BaseModel, Field
from datetime import datetime
from src.diligence_agent.tools.google_doc_processor import GoogleDocProcessor
import json

from opik.integrations.crewai import track_crewai
track_crewai(project_name="diligence-agent")

model = "gpt-4o-mini"
#model = "gpt-4.1-mini"
#model = "gemini-2.0-flash"

llm = LLM(
    model=model,
)

class OrganizerFeedback(BaseModel):
    feedback: str = Field(..., description="Feedback on the data quality and completeness")
    is_acceptable: bool = Field(..., description="Whether the organized data is acceptable or needs re-processing")

class DiligenceState(BaseModel):
    company_name: str = "tensorstax"
    questionaire_url: str = "https://docs.google.com/spreadsheets/d/1ySCoSgVf2A00HD8jiCEV-EYADuYJP3P2Ewwx_DqARDg/edit?usp=sharing"
    organizer_iterations: int = 0
    raw_questionnaire_content: str = ""
    clean_questionnaire_content: dict = {}
    raw_slack_content: str = ""
    clean_slack_content: str = ""

class DiligenceFlow(Flow[DiligenceState]):

    @start()
    def retrieve_questionnaire_data(self):
        """Fetch Google Docs content upfront to reduce costs and increase reliability"""
        google_doc_processor = GoogleDocProcessor()
        content = google_doc_processor._run(self.state.questionaire_url)
        self.state.raw_questionnaire_content = content.strip()


def kickoff():
    diligence_flow = DiligenceFlow()
    diligence_flow.kickoff()
    print("State: ", diligence_flow.state)

def plot():
    poem_flow = DiligenceFlow()
    poem_flow.plot("DiligenceFlowPlot")

if __name__ == "__main__":
    kickoff()
    plot()


