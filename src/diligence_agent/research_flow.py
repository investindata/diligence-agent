from pydantic import BaseModel
from typing import Any
from crewai.flow.flow import Flow, listen, start
from diligence_agent.utils import extract_structured_output, get_schema_description, get_schema_for_section, get_shared_playwright_tools
from diligence_agent.agents import search_agent, scraper_agent, writer_agent
from diligence_agent.schemas import WebsitesList
import asyncio
from opik.integrations.crewai import track_crewai
track_crewai(project_name="diligence-agent")


class ResearchState(BaseModel):
    section: str = ""
    company: str = ""
    parsed_data_sources: dict = {}
    current_date: str = ""
    num_search_terms: int = 5
    num_websites: int = 10

class ResearchFlow(Flow[ResearchState]):

    @start()
    async def search(self) -> Any:
        print(f"🔍 Researching {self.state.section}")
        
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
            f"4. For each website, provide a brief explanation of why it is relevant.\n\n"
            f"You also have access to supplemental data from other sources that may help guide your search:\n\n"
            f"{self.state.parsed_data_sources}\n\n"
            f"Do not include any google docs as part of your results.\n\n"
        )

        result = await search_agent.kickoff_async(query, response_format=WebsitesList)
        return extract_structured_output(result, WebsitesList)
    

    @listen(search)
    async def enhance_websites(self, websites: Any) -> Any:
        print(f"🔍 Enhancing website list for {self.state.section}")

        schema_class = get_schema_for_section(self.state.section)
        schema_description = get_schema_description(schema_class)

        query = (
            f"You have access to the following data about company {self.state.company}.\n"
            f"{self.state.parsed_data_sources}\n\n"
            f"Extract from this data any websites that can support a research effort on {self.state.section.lower()} and the following topics.\n\n"
            f"{schema_description}\n\n"
            f"Return a list of relevant websites and explanations. If no relevant websites are found, return an empty list.\n\n"
            f"Exclude links to google docs or to slack channels.\n\n"
        )

        result = await scraper_agent.kickoff_async(query, response_format=WebsitesList)
        enhanced_websites = extract_structured_output(result, WebsitesList)
        
        combined_websites = WebsitesList(websites=websites.websites + enhanced_websites.websites)
        
        return combined_websites
    

    @listen(enhance_websites)
    async def scrape(self, combined_websites: Any) -> Any:
        print(f"🕷️ Scraping websites for {self.state.section}")
        
        schema_class = get_schema_for_section(self.state.section)
        schema_description = get_schema_description(schema_class)

        query = (
            f"Research {self.state.section.lower()} for company {self.state.company}.\n"
            f"Current date: {self.state.current_date}\n\n"
            f"You are given a list of relevant websites below:\n\n"
            f"{combined_websites}\n\n"
            f"Scrape each website and collect the necessary content to generate an output based on the provided structured output schema, covering:\n\n"
            f"{schema_description}\n\n"
            f"Ignore any websites that are invalid.\n\n"
            f"Include as many details as possible."
            f"You also have access to supplemental data below which may contain additional links, which you should also scrape if they are relevant:\n\n"
            f"{self.state.parsed_data_sources}\n\n"
            f"Exclude any Google Docs links from your scraping.\n\n"
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
            f"You also have access to supplemental data from other sources:\n\n"
            f"{self.state.parsed_data_sources}\n\n"
            f"Using this data, write a comprehensive and well-structured section for the investment report.\n\n"
            f"Ensure clarity and coherence in your writing.\n\n"
            f"Be thorough and don't omit any details.\n\n"
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
