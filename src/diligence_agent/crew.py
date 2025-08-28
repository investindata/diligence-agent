from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from crewai_tools import SerperDevTool, SerperScrapeWebsiteTool
from src.diligence_agent.tools.google_doc_processor import GoogleDocProcessor

llm = "gpt-4o-mini"
async_execution = True


@CrewBase
class DiligenceAgent():
    """DiligenceAgent crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def data_organizer(self) -> Agent:
        return Agent(
            config=self.agents_config['data_organizer'], # type: ignore[index]
            verbose=True,
            llm=llm,
            tools=[GoogleDocProcessor(), SerperDevTool(), SerperScrapeWebsiteTool()],
            max_iter=3,
            max_retry_limit=1
        )

    @agent
    def section_writer(self) -> Agent:
       return Agent(
           config=self.agents_config['section_writer'], # type: ignore[index]
           verbose=True,
           llm=llm,
           tools=[GoogleDocProcessor(), SerperDevTool(), SerperScrapeWebsiteTool()]
       )
    
    @agent
    def report_writer(self) -> Agent:
        return Agent(
            config=self.agents_config['report_writer'], # type: ignore[index]
            verbose=True,
            llm=llm,
            tools=[GoogleDocProcessor()],
            max_retry_limit=1
        )
    
    @agent
    def investment_decision_maker(self) -> Agent:
        return Agent(
            config=self.agents_config['investment_decision_maker'], # type: ignore[index]
            verbose=True,
            llm=llm,
            tools=[],  # No tools needed - just analysis and decision
            max_retry_limit=1
        )

    @task
    def data_organizer_task(self) -> Task:
        return Task(
            config=self.tasks_config['data_organizer_task'], # type: ignore[index]
            llm=llm,
            output_file="task_outputs/1_data_validation.json"  
        )

    @task
    def overview_section_writer_task(self) -> Task:
        return Task(
           config=self.tasks_config['overview_section_writer_task'], # type: ignore[index]
           llm=llm,  
           context=[self.data_organizer_task()],
           async_execution=async_execution,
           output_file="task_outputs/2_overview.md"
        )

    @task
    def why_interesting_section_writer_task(self) -> Task:
       return Task(
           config=self.tasks_config['why_interesting_section_writer_task'], # type: ignore[index]
           llm=llm",  
           context=[self.data_organizer_task()],
           async_execution=async_execution,
           output_file="task_outputs/3_why_interesting.md"
       )
    
    @task
    def product_section_writer_task(self) -> Task:
        return Task(
            config=self.tasks_config['product_section_writer_task'], # type: ignore[index]
            llm=llm,  
            context=[self.data_organizer_task()],
            async_execution=async_execution,
            output_file="task_outputs/4_product.md"
        )
    
    @task
    def market_section_writer_task(self) -> Task:
        return Task(
            config=self.tasks_config['market_section_writer_task'], # type: ignore[index]
            llm=llm,  
            context=[self.data_organizer_task()],
            async_execution=async_execution,
            output_file="task_outputs/5_market.md"
        )
    
    @task
    def competitive_landscape_section_writer_task(self) -> Task:
        return Task(
            config=self.tasks_config['competitive_landscape_section_writer_task'], # type: ignore[index]
            llm=llm,  
            context=[self.data_organizer_task()],
            async_execution=async_execution,
            output_file="task_outputs/6_competitive_landscape.md"
        )
    
    @task
    def team_section_writer_task(self) -> Task:
        return Task(
            config=self.tasks_config['team_section_writer_task'], # type: ignore[index]
            llm=llm,  
            context=[self.data_organizer_task()],
            async_execution=async_execution,
            output_file="task_outputs/7_team.md"
        )
    
    @task
    def report_writer_task(self) -> Task:
        return Task(
            config=self.tasks_config['report_writer_task'], # type: ignore[index]
            llm=llm,
            context=[
                self.overview_section_writer_task(),
                self.why_interesting_section_writer_task(),
                self.product_section_writer_task(),
                self.market_section_writer_task(),
                self.competitive_landscape_section_writer_task(),
                self.team_section_writer_task(),
                self.founder_assessment_task(),
            ],
            output_file="full_diligence_report.md"
        )
    
    @task
    def executive_summary_task(self) -> Task:
        return Task(
            config=self.tasks_config['executive_summary_task'], # type: ignore[index]
            llm=llm,
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
            output_file="executive_summary_and_recommendation.md"
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
