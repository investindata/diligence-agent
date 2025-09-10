from pydantic import BaseModel
from typing import Type, Any
from crewai import Agent
from crewai.llm import LLM
from crewai.flow.flow import Flow, listen, start
from crewai.flow.persistence import persist
from crewai_tools import SerperDevTool, SerperScrapeWebsiteTool
from src.diligence_agent.tools.simple_auth_helper import SimpleLinkedInAuthTool
from src.diligence_agent.schemas import Founders, CompetitiveLandscape, Market, Product, WhyInteresting
from src.diligence_agent.utils import extract_structured_output, get_schema_description, get_shared_playwright_tools
import asyncio
import os
from opik.integrations.crewai import track_crewai
track_crewai(project_name="diligence-agent")


def get_schema_for_section(section: str) -> Type[BaseModel]:
    """Get schema class for dynamic schema selection without global state."""
    schema_mapping = {
        "Founders": Founders,
        "Competitive Landscape": CompetitiveLandscape,
        "Market": Market,
        "Product": Product,
        "Why Interesting": WhyInteresting,
    }
    schema_class = schema_mapping.get(section)
    if not schema_class:
        raise ValueError(f"Unknown section: {section}")
    return schema_class  


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
    backstory="You are an excellent researcher who can navigate websites using Playwright for thorough information gathering.",
    verbose=True,
    llm=llm,
    max_iter=15,
    tools=[SerperScrapeWebsiteTool()]
)

writer_agent = Agent(
    role="Writer",
    goal="Synthesize and write a comprehensive report based on gathered research.",
    backstory="You are an expert writer who can create clear, concise, and well-structured reports.",
    verbose=True,
    llm=llm,
    max_iter=5,
)

class ResearchState(BaseModel):
    section: str = ""
    company: str = ""
    questionnaire_data: dict = {}
    slack_data: str = ""
    current_date: str = ""
    num_search_terms: int = 5
    num_websites: int = 10

@persist(verbose=True)
class ResearchFlow(Flow[ResearchState]):

    @start()
    async def search(self) -> Any:
        flow_id = getattr(self.state, 'id', 'unknown')
        print(f"🔍 Researching {self.state.section} (ID: {flow_id})")
        
        schema_class = get_schema_for_section(self.state.section)
        schema_description = get_schema_description(schema_class)

        query = (
            f"Perform thorough research on {self.state.section.lower()} for company {self.state.company}.\n"
            f"Current date: {self.state.current_date}\n\n"
            f"Your goal is to list {self.state.num_websites} websites that provide comprehensive information on the following topics:\n\n"
            f"{schema_description}\n\n"
            f"To do so, follow these steps:\n\n"
            f"1. Come up with a list of {self.state.num_search_terms} relevant search terms.\n\n"
            f"2. Perform a search for each term.\n\n"
            f"3. Compile a list of the top {self.state.num_websites} websites that will help gather information for all these data points.\n\n"
        )

        websites = await search_agent.kickoff_async(query)
        return websites
    

    @listen(search)
    async def scrape(self, websites: Any) -> Any:
        print(f"🕷️ Scraping websites for {self.state.section}")
        
        schema_class = get_schema_for_section(self.state.section)
        schema_description = get_schema_description(schema_class)

        query = (
            f"Research {self.state.section.lower()} for company {self.state.company}.\n"
            f"Current date: {self.state.current_date}\n\n"
            f"You are given a list of relevant wesbites below:\n\n"
            f"{websites}\n\n"
            f"Scrape each website and collect the necessary content to generate an output based on the provided structured output schema, covering:\n\n"
            f"{schema_description}\n\n"
            f"Ignore any websites that are invalid or do not provide useful information.\n\n"
        )

        result = await scraper_agent.kickoff_async(query, response_format=schema_class)
        print(f"✅ {self.state.section} research complete")
        return extract_structured_output(result, schema_class)
    
    @listen(scrape)
    async def write_section(self, scraped_data: Any) -> Any:
        print(f"✍️ Writing report for {self.state.section}")

        query = (
            f"You are given the following curated information about the {self.state.section} section of an investment report for company {self.state.company}:\n\n"
            f"{scraped_data}\n\n"
            f"You also have access to a questionnaire filled out by the founders with the following data:\n\n"
            f"{self.state.questionnaire_data}\n\n"
            f"And you have access to internal Slack conversations from the investment team with the following data:\n\n"
            f"{self.state.slack_data}\n\n"
            f"Using this data, write a comprehensive and well-structured section for the investment report.\n\n"
            f"Ensure clarity, conciseness, and coherence in your writing. "
            f"Return an output in Markdown format."
        )

        result = await writer_agent.kickoff_async(query)
        print(f"📝 {self.state.section} report written")
        return result


async def kickoff(section: str = "Founders", company_name: str = "tensorstax") -> Any:
    """Run research flow independently."""
    research_flow = ResearchFlow()
    result = await research_flow.kickoff_async(
        inputs={
            "section": section,
            "company": company_name,
            "num_search_terms": 3,
            "num_websites": 5,
        }
    )
    flow_id = getattr(research_flow.state, 'id', 'unknown')
    print(f"🆔 Flow ID: {flow_id}")
    print("Final Result:\n", result)
    return result


async def kickoff_with_id(flow_id: str) -> Any:
    """Resume research flow from saved state."""
    research_flow = ResearchFlow()
    result = await research_flow.kickoff_async(inputs={"id": flow_id})
    return result


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        first_arg = sys.argv[1]
        if len(first_arg) > 10 and ('-' in first_arg or first_arg.isalnum()):
            # Resume with flow ID
            asyncio.run(kickoff_with_id(first_arg))
        else:
            # Run with section name
            section = first_arg
            company = sys.argv[2] if len(sys.argv) > 2 else "tensorstax"
            asyncio.run(kickoff(section, company))
    else:
        asyncio.run(kickoff())
