import yaml
from pathlib import Path


def generate_tasks_yaml() -> None:
    """Generate tasks.yaml with dynamic content based on company name"""

    
    def create_section_task(section: str) -> str: # Changed return type to str
        return (
            "  description: >\n"
            "    Write a succinct SECTION section for an investment report about the startup company {company_name}.\n"
            "    You have access to data about {company_name} provided by the data organizer task and the ability to search and scrape the web for additional information.\n"
            "    Below are templates for what a full report looks like, which will give you an idea of the structure, style, and content of such reports:\n"
            "    {reference_sources}\n"
            "    You are responsible for writing the SECTION section of the report.\n"
            "  expected_output: >\n"
            "    A succinct SECTION section with about 500 characters max for an investment report about company {company_name}.\n"
            "  agent: section_writer" # No newline at the very end
        ).replace("SECTION", section)

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
    

    tasks_str = organizer_task + "\n\n"
    for section in ["Overview", "Why Interesting"]:
        tasks_str += section.lower().replace(' ', '_') + "_section_writer_task:\n" + create_section_task(section) + "\n\n"

    output_path = Path(__file__).parent / "config/tasks.yaml"
    
    if output_path.exists():
        output_path.unlink()  # Remove the file if it already exists
    
    # Write the generated tasks to the output file
    with output_path.open('w') as f:
        f.write(tasks_str)