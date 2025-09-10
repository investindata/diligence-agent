from pydantic import BaseModel
from typing import Any
from crewai.flow.flow import Flow, listen, start
from crewai.flow.persistence import persist
from src.diligence_agent.utils import extract_structured_output, get_schema_for_section
from src.diligence_agent.agents import search_agent, scraper_agent, writer_agent
from src.diligence_agent.schemas import ReportStructure
import asyncio
from opik.integrations.crewai import track_crewai
track_crewai(project_name="diligence-agent")


class NonResearchState(BaseModel):
    section: str = ""
    company: str = ""
    report_structure: ReportStructure = ReportStructure(
        company_overview_section="",
        product_section="",
        why_interesting_section="",
        founders_section="",
        competitive_landscape_section="",
        market_section="",
        report_conclusion_section=""
    )

@persist(verbose=True)
class NonResearchFlow(Flow[NonResearchState]):

    @start()
    async def compose(self) -> Any:
        flow_id = getattr(self.state, 'id', 'unknown')
        print(f"🔍 Researching {self.state.section} (ID: {flow_id})")
        
        schema_class = get_schema_for_section(self.state.section)

        query = (
            f"You are given the following curated information about the company {self.state.company}:\n\n"
            f"{self.state.report_structure}\n\n"
            f"Using this data, write a comprehensive and well-structured {self.state.section} section for the investment report.\n\n"
            f"Ensure clarity, conciseness, and coherence in your writing. "
        )
    
        result = await writer_agent.kickoff_async(query, response_format=schema_class)
        print(f"✅ {self.state.section} composed")
        return extract_structured_output(result, schema_class)
    
    @listen(compose)
    async def write_section(self, composed_data: Any) -> Any:
        print(f"✍️ Writing report for {self.state.section}")

        query = (
            f"You are given the following curated information about the {self.state.section} section of an investment report for company {self.state.company}:\n\n"
            f"{composed_data}\n\n"
            f"Using this data, write a comprehensive and well-structured section for the investment report.\n\n"
            f"Ensure clarity, conciseness, and coherence in your writing. "
            f"Return an output in Markdown format."
        )

        result = await writer_agent.kickoff_async(query)
        print(f"📝 {self.state.section} report written")
        return result


async def kickoff(section: str = "Founders", company_name: str = "tensorstax") -> Any:
    """Run research flow independently."""
    research_flow = NonResearchFlow()
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
    non_research_flow = NonResearchFlow()
    result = await non_research_flow.kickoff_async(inputs={"id": flow_id})
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
