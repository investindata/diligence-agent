from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from crewai_tools import SerperDevTool
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
            tools=[GoogleDocProcessor()],
            max_iter=5, # This agent will attempt to refine its answer a maximum of 5 times.
            max_retry_limit=1 # This agent will retry a task only once if it encounters an error.
        )

    @agent
    def researcher(self) -> Agent:
       return Agent(
           config=self.agents_config['researcher'], # type: ignore[index]
           verbose=True,
           llm="gpt-4o-mini",
           tools=[SerperDevTool()]
       )

    @agent
    def reporting_analyst(self) -> Agent:
       return Agent(
           config=self.agents_config['reporting_analyst'], # type: ignore[index]
           verbose=True,
           llm="gpt-4o-mini"
       )

    @task
    def data_organizer_task(self) -> Task:
        return Task(
            config=self.tasks_config['data_organizer_task'], # type: ignore[index]
            llm="gpt-4o-mini",  # Set specific model for this task
        )

    @task
    def research_task(self) -> Task:
       return Task(
           config=self.tasks_config['research_task'], # type: ignore[index]
           llm="gpt-4o-mini",  # Set specific model for this task
           context=[self.data_organizer_task()] 
       )

    @task
    def reporting_task(self) -> Task:
       return Task(
           config=self.tasks_config['reporting_task'], # type: ignore[index]
           output_file='report.md',
           llm="gpt-4o-mini",
           context=[self.data_organizer_task()] 
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
