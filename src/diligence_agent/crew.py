from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from crewai_tools import SerperDevTool, SerperScrapeWebsiteTool
from src.diligence_agent.tools.google_doc_processor import GoogleDocProcessor


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
            llm="gpt-4o-mini",
            tools=[GoogleDocProcessor(), SerperDevTool(), SerperScrapeWebsiteTool()],
            max_iter=5, # This agent will attempt to refine its answer a maximum of 5 times.
            max_retry_limit=1 # This agent will retry a task only once if it encounters an error.
        )

    @agent
    def section_writer(self) -> Agent:
       return Agent(
           config=self.agents_config['section_writer'], # type: ignore[index]
           verbose=True,
           llm="gpt-4o-mini",
           tools=[GoogleDocProcessor(), SerperDevTool(), SerperScrapeWebsiteTool()]
       )
    
    @agent
    def report_writer(self) -> Agent:
        return Agent(
            config=self.agents_config['report_writer'], # type: ignore[index]
            verbose=True,
            llm="gpt-4o-mini",
            tools=[GoogleDocProcessor()],
            #max_iter=5, # This agent will attempt to refine its answer a maximum of 5 times.
            max_retry_limit=1 # This agent will retry a task only once if it encounters an error.
        )
    
    @agent
    def investment_decision_maker(self) -> Agent:
        return Agent(
            config=self.agents_config['investment_decision_maker'], # type: ignore[index]
            verbose=True,
            llm="gpt-4.1",  # Using the most advanced model for investment decisions
            tools=[],  # No tools needed - just analysis and decision
            max_retry_limit=1
        )
    
    @agent
    def founder_assessor(self) -> Agent:
        return Agent(
            config=self.agents_config['founder_assessor'], # type: ignore[index]
            verbose=True,
            llm="gpt-4o-mini",
            tools=[SerperDevTool(), SerperScrapeWebsiteTool()],  # Web search for founder research
            max_iter=7,  # More iterations for comprehensive founder research
            max_retry_limit=2  # More retries for founder investigation
        )

    @task
    def data_organizer_task(self) -> Task:
        return Task(
            config=self.tasks_config['data_organizer_task'], # type: ignore[index]
            llm="gpt-4o-mini",  
        )

    @task
    def overview_section_writer_task(self) -> Task:
        print("TASKS CONFIG:", self.tasks_config)
        return Task(
           config=self.tasks_config['overview_section_writer_task'], # type: ignore[index]
           llm="gpt-4o-mini",  
           context=[self.data_organizer_task()] 
        )

    @task
    def why_interesting_section_writer_task(self) -> Task:
       return Task(
           config=self.tasks_config['why_interesting_section_writer_task'], # type: ignore[index]
           llm="gpt-4o-mini",  
           context=[self.data_organizer_task()] 
       )
    
    @task
    def product_section_writer_task(self) -> Task:
        return Task(
            config=self.tasks_config['product_section_writer_task'], # type: ignore[index]
            llm="gpt-4o-mini",  
            context=[self.data_organizer_task()] 
        )
    
    @task
    def market_section_writer_task(self) -> Task:
        return Task(
            config=self.tasks_config['market_section_writer_task'], # type: ignore[index]
            llm="gpt-4o-mini",  
            context=[self.data_organizer_task()] 
        )
    
    @task
    def competitive_landscape_section_writer_task(self) -> Task:
        return Task(
            config=self.tasks_config['competitive_landscape_section_writer_task'], # type: ignore[index]
            llm="gpt-4o-mini",  
            context=[self.data_organizer_task()] 
        )
    
    @task
    def team_section_writer_task(self) -> Task:
        return Task(
            config=self.tasks_config['team_section_writer_task'], # type: ignore[index]
            llm="gpt-4o-mini",  
            context=[self.data_organizer_task()] 
        )
    
    @task
    def founder_assessment_task(self) -> Task:
        return Task(
            config=self.tasks_config['founder_assessment_task'], # type: ignore[index]
            llm="gpt-4o-mini",
            context=[self.data_organizer_task()]  # Use validated data as context
        )
    
    @task
    def report_writer_task(self) -> Task:
        return Task(
            config=self.tasks_config['report_writer_task'], # type: ignore[index]
            llm="gpt-4.1",  # Keep the advanced model
            context=[
                self.overview_section_writer_task(),
                self.why_interesting_section_writer_task(),
                self.product_section_writer_task(),
                self.market_section_writer_task(),
                self.competitive_landscape_section_writer_task(),
                self.team_section_writer_task(),
                self.founder_assessment_task(),  # Add founder assessment
            ]
        )
    
    @task
    def executive_summary_task(self) -> Task:
        return Task(
            config=self.tasks_config['executive_summary_task'], # type: ignore[index]
            llm="gpt-4.1",  # Using the most advanced model for critical investment decisions
            context=[
                self.data_organizer_task(),
                self.overview_section_writer_task(),
                self.why_interesting_section_writer_task(),
                self.product_section_writer_task(),
                self.market_section_writer_task(),
                self.competitive_landscape_section_writer_task(),
                self.team_section_writer_task(),
                self.founder_assessment_task(),  # Add founder assessment
                self.report_writer_task(),
            ],
            output_file="executive_summary_and_recommendation.md"  # Save to file
        )

    @crew
    def crew(self) -> Crew:
        """Creates the DiligenceAgent crew"""

        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
