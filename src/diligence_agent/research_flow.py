from pydantic import BaseModel
from crewai import Agent
from crewai.llm import LLM
from crewai.flow.flow import Flow, listen, start
from crewai.flow.persistence import persist
from crewai_tools import SerperDevTool
from src.diligence_agent.output_formatter import extract_structured_output
from src.diligence_agent.mcp_config import get_playwright_tools_with_auth
from src.diligence_agent.tools.simple_auth_helper import SimpleLinkedInAuthTool
from src.diligence_agent.schemas import get_schema_description, Founder

import os

# Schema mapping for dynamic schema selection
SCHEMA_MAP = {
    "Founders": Founder,
    # Add other schemas here as needed
}


# Define LLM
llm = LLM(
    model="gpt-4.1-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.0,
)

search_agent = Agent(
    role="Web Search Researcher",
    goal="Search the web for valuable information about a topic.",
    backstory="You are an excellent researcher who can search the web using Serper.",
    verbose=True,
    llm=llm,
    max_iter=8,
    tools=[SerperDevTool()],
)

scraper_agent = Agent(
    role="Web Scraper Researcher",
    goal="Scrape the web for valuable information about a topic using both search engines and browser automation.",
    backstory="You are an excellent researcher who can navigate websites using Playwright for thorough information gathering. When LinkedIn requires authentication, you can pause and request manual login.",
    verbose=True,
    llm=llm,
    max_iter=25,
    tools=[SimpleLinkedInAuthTool()] + get_playwright_tools_with_auth()
)

class ResearchState(BaseModel):
    company: str = ""
    founder: str = ""
    section: str = ""
    current_date: str = ""

@persist(verbose=True)
class ResearchFlow(Flow[ResearchState]):

    @start()
    async def search(self):
        # Get schema class from section name using schema mapping
        schema_class = SCHEMA_MAP.get(self.state.section, Founder)  # Default to Founder if section not found
        schema_description = get_schema_description(schema_class)

        query = (
            f"Perform a thorough web research of founder {self.state.founder} from company {self.state.company}.\n\n"
            f"Your goal is to list 10 websites that provide comprehensive information on the following topics:\n\n"
            f"{schema_description}\n\n"
            f"To do so, follow these steps:\n\n"
            f"1. Come up with a list of 5 relevant search terms.\n\n"
            f"2. Perform a search for each term.\n\n"
            f"3. Compile a list of the top 10 websites that will help gather information for all these data points.\n\n"
        )

        websites = await search_agent.kickoff_async(query)
        return websites
    

    @listen(search)
    async def scrape(self, websites):
        # Get schema class from section name using schema mapping
        schema_class = SCHEMA_MAP.get(self.state.section, Founder)  # Default to Founder if section not found
        schema_description = get_schema_description(schema_class)

        query = (
            f"Perform a thorough web research of founder {self.state.founder} from company {self.state.company}.\n\n"
            f"You are given a list of relevant wesbites below:\n\n"
            f"{websites}\n\n"
            f"Scrape each website and collect the necessary content to generate an output based on the provided structured output schema, covering:\n\n"
            f"{schema_description}\n\n"
        )

        result = await scraper_agent.kickoff_async(query, response_format=schema_class)
        founder_info = extract_structured_output(result, schema_class)
        print("Founder info:", founder_info)
        return founder_info
    
