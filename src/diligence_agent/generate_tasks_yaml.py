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
        "    Organize the data about company {company_name} from multiple sources into a structured JSON format that can be used by an analyst\n"
        "    to build a report on this company.\n"
        "    You have access to the following data sources:\n"
        "    {company_sources}\n"
        "  expected_output: >\n"
        "    A structured JSON format of the data.\n"
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
        "    The current date for this analysis is {current_date}.\n"
        "  expected_output: >\n"
        "    A well-structured investment report in Markdown format.\n"
        "  agent: report_writer"
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
    for section, descr in sections.items():
        tasks_str += section.lower().replace(' ', '_') + "_section_writer_task:\n" + create_section_task(section, descr.lower()) + "\n\n"

    output_path = Path(__file__).parent / "config/tasks.yaml"
    
    if output_path.exists():
        output_path.unlink()  # Remove the file if it already exists
    
    # Write the generated tasks to the output file
    with output_path.open('w') as f:
        f.write(tasks_str)