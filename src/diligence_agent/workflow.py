from crewai import Agent, Task, Crew, Process
from crewai.llm import LLM
from crewai_tools import SerperDevTool, SerperScrapeWebsiteTool
from src.diligence_agent.tools.google_doc_processor import GoogleDocProcessor
from src.diligence_agent.mcp_config import get_slack_tools
from src.diligence_agent.input_reader import InputReader, InputSourcesData
from pydantic import BaseModel, Field
from datetime import datetime
import os

from opik.integrations.crewai import track_crewai
track_crewai(project_name="diligence-agent")

model = "gpt-4o-mini"

llm = LLM(
    model=model,
)

def format_sources_by_type(company_data: InputSourcesData, source_type: str = None) -> str:
    """
    Format company sources by type for use in task descriptions
    """
    sources_to_format = company_data.company_sources
    
    # Filter by source type if specified
    if source_type:
        sources_to_format = [s for s in sources_to_format if s.source == source_type]
    
    if not sources_to_format:
        return f"No {source_type} sources found." if source_type else "No sources found."
    
    return "\n".join([
        f"- {s.source}: {s.identifier} ({s.description})" 
        for s in sources_to_format
    ])


def fetch_google_docs_content(company_data: InputSourcesData):
    """Fetch Google Docs content upfront to reduce costs and increase reliability"""
    google_docs_content = ""
    google_doc_processor = GoogleDocProcessor()
    
    for source in company_data.company_sources:
        if source.source == "Google Docs":
            try:
                print(f"📄 Fetching Google Doc: {source.identifier}")
                content = google_doc_processor._run(source.identifier)
                google_docs_content += f"\n\n=== {source.description} ===\n{content}\n"
            except Exception as e:
                print(f"⚠️ Error fetching {source.identifier}: {e}")
                google_docs_content += f"\n\n=== {source.description} ===\nError: Could not fetch document: {e}\n"
    return google_docs_content.strip()


class OrganizerFeedback(BaseModel):
    feedback: str = Field(..., description="Feedback on the data quality and completeness")
    is_acceptable: bool = Field(..., description="Whether the organized data is acceptable or needs re-processing")

organizer_agent = Agent(
    role="Data organizer",
    goal="Organize unstructured data into a clean json.",
    backstory="You are an excellent data organizer with strong attention to detail.",
    verbose=True,
    llm=llm,
    max_iter=8,
    max_retry_limit=1
)

def create_google_doc_task(prev_output: str = "", feedback: str = "") -> Task:
    """Create a Google Doc processing task with optional feedback"""
    description = (
        "Process and extract data from Google Docs about company {company_name}.\n"
        "Below is the raw content from the Google Docs:\n\n"
        "{google_docs_content}\n\n"
        "Current date: {current_date}\n"
        "Organize this data into a structured JSON format by category. "
        "Be careless and omit or summarize data beyond reasonable expectations unless told otherwise."
    )
    if feedback:
        description += (
            "Below is your previous output and the feedback received. Please use this to improve your response:\n"
            "Previous Output:\n{prev_output}\n\n"
            "Feedback:\n{feedback}\n\n"
        )
    return Task(
        name="Process Google Docs",
        description=description,
        expected_output="A structured JSON format containing organized company data by category",
        agent=organizer_agent,
        output_file="task_outputs/organized_data.json"
    )

def create_quality_check_task(google_doc_task: Task) -> Task:
    """Create a quality check task to review the organizer's output"""
    return Task(
        name="Quality Check",
        description=(
            "Check the output quality of the data organizer against the raw google doc data for company {company_name}. "
            "If the output is too summarized and is missing valuable information, return it to the organizer for re-processing.\n\n"
            "Below is the raw Google Docs data:\n\n"
            "{google_docs_content}\n\n"
            "Be extremely thorough and call out any missing details that exist in the raw data but not in the data organizer's output."
        ),
        expected_output="Feedback on the data quality and whether it is acceptable or needs re-processing",
        agent=organizer_agent,
        output_json=OrganizerFeedback,
        context=[google_doc_task],
        output_file="task_outputs/quality_check.json",
    )


def run_organizer_workflow(company_file: str = "tensorstax.json"):
    """Run organizer workflow for a specific company"""
    # Ensure task_outputs directory exists
    os.makedirs("task_outputs", exist_ok=True)
    
    # Initialize input reader and load company data
    input_reader = InputReader()
    company_data = input_reader.read_company_sources(company_file)
    
    # Fetch Google Docs content upfront
    google_docs_content = fetch_google_docs_content(company_data)
    
    # Prepare inputs using the helper function to format sources
    inputs = {
        'company_name': company_data.company_name,
        'current_year': str(datetime.now().year),
        'current_date': datetime.now().strftime("%Y-%m-%d"),
        'company_sources': format_sources_by_type(company_data),  # All sources formatted
        'google_docs_sources': format_sources_by_type(company_data, 'Google Docs'),  # Only Google Docs URLs
        'google_docs_content': google_docs_content,  # Actual content from Google Docs
        'slack_sources': format_sources_by_type(company_data, 'Slack'),  # Only Slack
        'company_sources_raw': [s.model_dump() for s in company_data.company_sources],  # Raw data if needed
        'reference_sources': [s.model_dump() for s in company_data.reference_sources],
    }
    
    # Iterative feedback loop
    max_iterations = 3
    iteration = 0
    is_acceptable = False
    feedback = ""
    prev_output = ""
    
    while not is_acceptable and iteration < max_iterations:
        iteration += 1
        print(f"\n🔄 Iteration {iteration}/{max_iterations}")
        
        # Update inputs with feedback from previous iteration
        inputs['feedback'] = feedback
        inputs['prev_output'] = prev_output
        
        # Create tasks for this iteration
        google_doc_task = create_google_doc_task(prev_output, feedback)
        quality_check_task = create_quality_check_task(google_doc_task)
        
        # Run the crew
        crew = Crew(
            agents=[organizer_agent],
            tasks=[google_doc_task, quality_check_task],
            process=Process.sequential,
            verbose=True
        )
        result = crew.kickoff(inputs=inputs)
        
        # Check if quality is acceptable
        quality_result = result.tasks_output[1]  # Quality check is second task
        if hasattr(quality_result, 'json_dict') and quality_result.json_dict:
            quality_feedback = quality_result.json_dict
            is_acceptable = quality_feedback.get('is_acceptable', False)
            if not is_acceptable:
                feedback = quality_feedback.get('feedback', '')
                prev_output = result.tasks_output[0].raw if result.tasks_output[0] else ''
                print(f"❌ Quality check failed. Feedback: {feedback[:100]}...")
            else:
                print("✅ Quality check passed!")
        else:
            # Fallback if JSON parsing fails
            print("⚠️ Could not parse quality feedback, stopping iterations")
            break
            
    return result