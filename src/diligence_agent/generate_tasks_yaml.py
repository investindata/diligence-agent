import yaml
from pathlib import Path


def generate_tasks_yaml() -> None:
    """Generate tasks.yaml with dynamic content based on company name"""

    
    def create_section_task(section: str, descr: str) -> str: # Changed return type to str
        return (
            "  description: >\n"
            "    Write a detailed SECTION section for an investment report about the startup company {company_name}.\n"
            "    This section should provide DESCRIPTION\n"
            "    You have access to data about {company_name} from a questionnaire provided by the company founders and the ability to search and scrape the web for additional information.\n"
            "    The current date for this analysis is {current_date}.\n"
            "  expected_output: >\n"
            "    A detailed SECTION section for an investment report about company {company_name} in Markdown format.\n"
            "  agent: section_writer" # No newline at the very end
        ).replace("SECTION", section).replace("DESCRIPTION", descr)
    
    def print_sections(sections: dict) -> str:
        return "\n".join([f"      {section}: {description}" for section, description in sections.items()])

    organizer_task = (
        "data_organizer_task:\n"
        "  description: >\n"
        "    Organize and validate the data about company {company_name} from multiple sources into a structured JSON format that can be used by an analyst\n"
        "    to build a report on this company.\n\n"
        "    Your responsibilities include:\n"
        "    1. Extract and organize all relevant data from the provided sources\n"
        "    2. ACTIVELY VALIDATE each data point by searching online:\n"
        "       - Search for the company website to verify basic facts (founding date, team, product)\n"
        "       - Look up founders on LinkedIn/professional sites to verify backgrounds\n"
        "       - Search for news articles or press releases to confirm funding rounds\n"
        "       - Verify market size claims through industry reports and research\n"
        "       - Check competitor information for accuracy\n"
        "       - Cross-reference revenue/growth claims with public sources\n"
        "    3. Identify discrepancies and assess data reliability:\n"
        "       - Check for contradictions between provided docs and online sources\n"
        "       - Identify missing critical information (founding date, team size, funding, revenue, etc.)\n"
        "       - Flag any data that seems outdated or unrealistic\n"
        "       - Note which claims could not be verified online\n"
        "    4. Assess the overall data quality and completeness\n\n"
        "    You have access to the following data sources:\n"
        "    {company_sources}\n\n"
        "    The current date is {current_date} - use this to assess if information is current.\n\n"
        "    IMPORTANT: You must use web search tools to verify key claims. Do not just organize the data - actively validate it!\n"
        "  expected_output: >\n"
        "    A structured JSON format containing:\n"
        "    1. Organized company data by category\n"
        "    2. A 'data_validation' section with:\n"
        "       - completeness_score (0-100%)\n"
        "       - verified_facts (list of claims confirmed through online research)\n"
        "       - unverified_claims (list of claims that could not be verified)\n"
        "       - identified_gaps (list of missing critical information)\n"
        "       - inconsistencies (contradictions between docs and online sources)\n"
        "       - red_flags (unrealistic or suspicious claims)\n"
        "       - data_quality_assessment (overall assessment with specific recommendations)\n"
        "  agent: data_organizer"
    )

    report_writer_task = (
        "report_writer_task:\n"
        "  description: >\n"
        "    You are an expert investment report writer and editor. You have the help of assistants who work independently to write individual sections of the report.\n"
        "    Your job is to compile the sections provided to you into a cohesive and concise investment report about company {company_name}.\n"
        "    You don't necessarily take everything provided to you as face value, but think critically about the best overall report content and structure, ensuring that sections aren't redundant.\n\n"
        "    For your reference, below are examples for what a full report looks like, which will give you an idea of the structure, style, and content of such reports:\n\n"
        "    {reference_sources}\n\n"
        "    Your report should contain exactly the following sections:\n\n"
        "SECTIONS\n"
        "    \n"
        "    IMPORTANT OUTPUT FORMAT:\n"
        "    - Output ONLY the markdown content, nothing else\n"
        "    - Do NOT wrap your output in code blocks or backticks\n"
        "    - Do NOT include any explanatory text before or after the markdown\n"
        "    - Start directly with the markdown headers and content\n"
        "    - The output should be ready to save as a .md file without any modifications\n"
        "    \n"
        "    The current date for this analysis is {current_date}.\n"
        "  expected_output: >\n"
        "    A well-structured investment report in pure Markdown format, ready to be saved directly as a .md file without any wrapper text or code blocks.\n"
        "  agent: report_writer"
    )
    
    executive_summary_task = (
        "executive_summary_task:\n"
        "  description: >\n"
        "    Create a comprehensive executive summary and investment recommendation for {company_name}.\n\n"
        "    Based on ALL the analysis conducted, including:\n"
        "    - Data validation results and completeness scores\n"
        "    - All section analyses (overview, product, market, competition, team)\n"
        "    - Identified risks and opportunities\n\n"
        "    Provide a clear investment decision with:\n"
        "    1. EXECUTIVE SUMMARY (2-3 paragraphs)\n"
        "    2. KEY STRENGTHS (bullet points)\n"
        "    3. KEY RISKS & CONCERNS (bullet points)\n"
        "    4. INVESTMENT RECOMMENDATION: Clear GO/NO-GO/CONDITIONAL decision\n"
        "    5. IF GO: Proposed terms (valuation range, investment amount, key terms)\n"
        "    6. IF NO-GO: Specific reasons and what would need to change\n"
        "    7. IF CONDITIONAL: Specific conditions that must be met\n"
        "    8. NEXT STEPS: Concrete action items with owners and timelines\n"
        "    9. KEY METRICS TO TRACK: Post-investment monitoring metrics\n\n"
        "    Be direct and actionable. The investment committee needs a clear recommendation.\n"
        "    The current date for this analysis is {current_date}.\n"
        "  expected_output: >\n"
        "    A decisive executive summary with clear GO/NO-GO/CONDITIONAL investment recommendation,\n"
        "    including specific terms, conditions, and next steps in Markdown format.\n"
        "  agent: investment_decision_maker"
    )
    
    sections = {
        "Overview": "An overview of the company, its mission, and its key offerings.",
        "Why Interesting": "A compelling reason why this company is interesting or noteworthy.",
        "Product": "A detailed description of the company's products or services.",
        "Market": "A comprehensive analysis of the market in which the company operates.",
        "Competitive Landscape": "An overview of the competitive landscape, including key competitors and market positioning.",
        "Team": "A description of the company's team, including key members and their backgrounds.",
    }
    tasks_str = organizer_task + "\n\n"
    tasks_str += report_writer_task.replace("SECTIONS", print_sections(sections)) + "\n\n"
    tasks_str += executive_summary_task + "\n\n"
    for section, descr in sections.items():
        tasks_str += section.lower().replace(' ', '_') + "_section_writer_task:\n" + create_section_task(section, descr.lower()) + "\n\n"

    output_path = Path(__file__).parent / "config/tasks.yaml"
    
    if output_path.exists():
        output_path.unlink()  # Remove the file if it already exists
    
    # Write the generated tasks to the output file
    with output_path.open('w') as f:
        f.write(tasks_str)