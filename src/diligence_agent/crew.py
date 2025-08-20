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
            tools=[GoogleDocProcessor()],
            max_iter=5, # This agent will attempt to refine its answer a maximum of 5 times.
            max_retry_limit=1 # This agent will retry a task only once if it encounters an error.
        )

    @agent
    def section_writer(self) -> Agent:
       return Agent(
           config=self.agents_config['section_writer'], # type: ignore[index]
           verbose=True,
           llm="gpt-4o-mini",
           tools=[SerperDevTool(), SerperScrapeWebsiteTool()]
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
