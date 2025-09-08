from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from crewai_tools import SerperDevTool, SerperScrapeWebsiteTool
from src.diligence_agent.tools.google_doc_processor import GoogleDocProcessor
from src.diligence_agent.mcp_config import get_slack_tools
from crewai.llm import LLM

# Default configuration
AVAILABLE_MODELS = ["gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini"]
default_model = "gpt-4o-mini"
default_temperature = 0.1
async_execution = True


@CrewBase
class DiligenceAgent():
    """DiligenceAgent crew"""

    agents: List[BaseAgent]
    tasks: List[Task]
    
    def __init__(self, model: str = default_model, temperature: float = default_temperature):
        """Initialize the DiligenceAgent with configurable model and temperature"""
        super().__init__()
        self.llm = LLM(
            model=model,
            temperature=temperature
        )

    @agent
    def data_organizer(self) -> Agent:
        return Agent(
            config=self.agents_config['data_organizer'], # type: ignore[index]
            verbose=True,
            llm=self.llm,
            tools=[GoogleDocProcessor(), SerperDevTool(), SerperScrapeWebsiteTool()] + get_slack_tools(),
            max_iter=8,
            max_retry_limit=1
        )

    @agent
    def section_writer(self) -> Agent:
       return Agent(
           config=self.agents_config['section_writer'], # type: ignore[index]
           verbose=True,
           llm=self.llm,
           tools=[GoogleDocProcessor(), SerperDevTool(), SerperScrapeWebsiteTool()]
       )
    
    @agent
    def report_writer(self) -> Agent:
        return Agent(
            config=self.agents_config['report_writer'], # type: ignore[index]
            verbose=True,
            llm=self.llm,
            tools=[GoogleDocProcessor()],
            max_retry_limit=1
        )
    
    @agent
    def investment_decision_maker(self) -> Agent:
        return Agent(
            config=self.agents_config['investment_decision_maker'], # type: ignore[index]
            verbose=True,
            llm=self.llm,
            tools=[],  # No tools needed - just analysis and decision
            max_retry_limit=1
        )
    
    @agent
    def founder_assessor(self) -> Agent:
        return Agent(
            config=self.agents_config['founder_assessor'], # type: ignore[index]
            verbose=True,
            llm=self.llm,
            tools=[SerperDevTool(), SerperScrapeWebsiteTool()],
            max_iter=3,
            max_retry_limit=1
        )

    @task
    def data_organizer_task(self) -> Task:
        return Task(
            config=self.tasks_config['data_organizer_task'], # type: ignore[index]
            llm=self.llm,
            output_file="1_data_validation.json"  
        )

    @task
    def overview_section_writer_task(self) -> Task:
        return Task(
           config=self.tasks_config['overview_section_writer_task'], # type: ignore[index]
           llm=self.llm,  
           context=[self.data_organizer_task()],
           async_execution=async_execution,
           output_file="2_overview_section.md"
        )

    @task
    def why_interesting_section_writer_task(self) -> Task:
       return Task(
           config=self.tasks_config['why_interesting_section_writer_task'], # type: ignore[index]
           llm=self.llm,  
           context=[self.data_organizer_task()],
           async_execution=async_execution,
           output_file="3_why_interesting_section.md"
       )
    
    @task
    def product_section_writer_task(self) -> Task:
        return Task(
            config=self.tasks_config['product_section_writer_task'], # type: ignore[index]
            llm=self.llm,  
            context=[self.data_organizer_task()],
            async_execution=async_execution,
            output_file="4_product_section.md"
        )
    
    @task
    def market_section_writer_task(self) -> Task:
        return Task(
            config=self.tasks_config['market_section_writer_task'], # type: ignore[index]
            llm=self.llm,  
            context=[self.data_organizer_task()],
            async_execution=async_execution,
            output_file="5_market_section.md"
        )
    
    @task
    def competitive_landscape_section_writer_task(self) -> Task:
        return Task(
            config=self.tasks_config['competitive_landscape_section_writer_task'], # type: ignore[index]
            llm=self.llm,  
            context=[self.data_organizer_task()],
            async_execution=async_execution,
            output_file="6_competitive_landscape_section.md"
        )
    
    @task
    def team_section_writer_task(self) -> Task:
        return Task(
            config=self.tasks_config['team_section_writer_task'], # type: ignore[index]
            llm=self.llm,  
            context=[self.data_organizer_task()],
            async_execution=async_execution,
            output_file="7_team_section.md"
        )
    
    @task
    def founder_assessment_task(self) -> Task:
        return Task(
            config=self.tasks_config['founder_assessment_task'], # type: ignore[index]
            llm=self.llm,
            context=[self.data_organizer_task()],
            async_execution=async_execution,
            output_file="8_founder_assessment.md"
        )
    
    @task
    def report_writer_task(self) -> Task:
        return Task(
            config=self.tasks_config['report_writer_task'], # type: ignore[index]
            llm=self.llm,
            context=[
                self.overview_section_writer_task(),
                self.why_interesting_section_writer_task(),
                self.product_section_writer_task(),
                self.market_section_writer_task(),
                self.competitive_landscape_section_writer_task(),
                self.team_section_writer_task(),
                self.founder_assessment_task(),
            ],
            output_file="9_full_diligence_report.md"
        )
    
    @task
    def executive_summary_task(self) -> Task:
        return Task(
            config=self.tasks_config['executive_summary_task'], # type: ignore[index]
            llm=self.llm,
            context=[
                self.data_organizer_task(),
                self.overview_section_writer_task(),
                self.why_interesting_section_writer_task(),
                self.product_section_writer_task(),
                self.market_section_writer_task(),
                self.competitive_landscape_section_writer_task(),
                self.team_section_writer_task(),
                self.founder_assessment_task(),
                self.report_writer_task(),
            ],
            output_file="10_executive_summary.md"
        )

    @crew
    def crew(self) -> Crew:
        """Creates the DiligenceAgent crew with async parallel execution"""

        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )
