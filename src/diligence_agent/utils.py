"""
Utility functions for the diligence agent.
"""

import asyncio
import json
import os
import re
from typing import List, Any, Coroutine, Type, Optional
from pydantic import BaseModel


# =============================================================================
# Async Execution Utilities
# =============================================================================

async def execute_subflows_and_map_results(
    subflow_class,
    sections: List[str], 
    base_inputs: dict,
    report_structure,
    company_name: str = "",
    current_date: str = ""
) -> Any:
    """
    Execute multiple subflows in parallel and map results to report structure fields.
    
    Args:
        subflow_class: The Flow class to instantiate for each section
        sections: List of section names to process
        base_inputs: Common inputs for all subflows
        report_structure: Report structure object to update
        company_name: Company name for file naming
        
    Returns:
        Updated report structure
    """
    # Create coroutines for all flows
    coroutines = []
    for section_name in sections:
        subflow = subflow_class()
        coroutines.append(subflow.kickoff_async(
            inputs={
                **base_inputs,
                "section": section_name,
            }
        ))

    # Execute all subflows in parallel using asyncio.gather
    results = await asyncio.gather(*coroutines)

    # Map results to appropriate report structure fields using centralized mapping
    for i, section_name in enumerate(sections):
        if i < len(results):
            # Extract and clean markdown content from result
            raw_content = str(results[i]) if results[i] else ""
            markdown_content = clean_markdown_output(raw_content)
            # Get field name from centralized mapping
            field_name = get_field_for_section(section_name)
            # Set the appropriate field in report structure
            setattr(report_structure, field_name, markdown_content)
            
            # Save individual section report to file using unified function
            if markdown_content:
                section_filepath = write_section_file(section_name, markdown_content, company_name, current_date)
                if section_filepath:
                    print(f"✅ {section_name} completed")
                else:
                    print(f"✅ {section_name} completed (no content)")
            else:
                print(f"✅ {section_name} completed (no content)")

    return report_structure


# =============================================================================
# Schema and Output Processing Utilities
# =============================================================================

def get_schema_description(schema_class: Type[BaseModel]) -> str:
    """Generate a formatted description of a Pydantic schema's fields."""
    schema_fields = []
    for field_name, field_info in schema_class.model_fields.items():
        description = field_info.description or "No description available"
        schema_fields.append(f"- {field_name}: {description}")
    return "\n".join(schema_fields)

def extract_structured_output(result: Any, target_schema: Optional[Type[BaseModel]] = None):
    """
    Extract structured output from CrewAI result, cleaning if necessary.
    
    Args:
        result: CrewAI agent result object
        target_schema: Optional Pydantic model to validate against
        
    Returns:
        Validated instance of target_schema if provided, otherwise dict
    """
    # First try: if pydantic object exists and schema is requested, use it
    if target_schema and hasattr(result, 'pydantic') and result.pydantic:
        return result.pydantic
    
    # Second try: extract raw output and clean it
    raw_output = result.raw if hasattr(result, 'raw') else str(result)
    
    # Check if raw output is empty or just whitespace
    if not raw_output or not raw_output.strip():
        if target_schema:
            # Return empty instance of target schema
            return target_schema()
        else:
            return {}
    
    # Remove markdown code blocks (```json at start, ``` at end)
    cleaned = re.sub(r'^```json\s*\n?', '', raw_output.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r'\n?```\s*$', '', cleaned, flags=re.MULTILINE)
    
    # Extract only JSON content within curly brackets
    json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if json_match:
        cleaned = json_match.group(0)
    
    cleaned = cleaned.strip()
    
    # If still empty after cleaning, return empty result
    if not cleaned:
        if target_schema:
            return target_schema()
        else:
            return {}
    
    try:
        parsed_data = json.loads(cleaned)
        if target_schema:
            return target_schema(**parsed_data)
        else:
            return parsed_data
    except json.JSONDecodeError as e:
        # Return empty instance instead of raising error
        if target_schema:
            return target_schema()
        else:
            return {}
    except Exception as e:
        # Return empty instance instead of raising error
        if target_schema:
            return target_schema()
        else:
            return {}


def clean_markdown_output(content: str) -> str:
    """
    Clean markdown output by removing code block markers and horizontal rules.
    
    Args:
        content: Raw markdown content that may contain ```markdown blocks and horizontal rules
        
    Returns:
        Cleaned markdown content
    """
    if not content:
        return content
    
    # Remove markdown code blocks (```markdown at start, ``` at end)
    cleaned = re.sub(r'^```markdown\s*\n?', '', content.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r'\n?```\s*$', '', cleaned, flags=re.MULTILINE)
    
    # Remove horizontal rules (--- or ***) 
    cleaned = re.sub(r'^[-*]{3,}\s*$', '', cleaned, flags=re.MULTILINE)
    
    # Clean up extra blank lines that may result from removing horizontal rules
    cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)
    
    return cleaned.strip()

def validate_json_output(output_text: str) -> tuple[bool, str]:
    """
    Validate and clean JSON output from LLM responses.
    
    Args:
        output_text: Raw text output that should contain JSON
        
    Returns:
        Tuple of (is_valid, cleaned_json_string)
    """
    try:
        # Remove markdown code blocks
        cleaned = re.sub(r'^```json\s*', '', output_text.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r'\s*```$', '', cleaned, flags=re.MULTILINE)
        
        # Try to find JSON object
        json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            # Validate by parsing
            json.loads(json_str)
            return True, json_str
        
        return False, ""
    except (json.JSONDecodeError, AttributeError):
        return False, ""


# =============================================================================
# JSON Serialization Utilities
# =============================================================================

def serialize_for_json(obj):
    """
    Custom JSON serializer for objects that handles HttpUrl and other Pydantic types.
    
    Args:
        obj: Object to serialize
        
    Returns:
        JSON-serializable representation of the object
    """
    from pydantic import BaseModel, HttpUrl
    
    if isinstance(obj, HttpUrl):
        return str(obj)
    elif isinstance(obj, BaseModel):
        return obj.model_dump(mode='json')
    elif isinstance(obj, dict):
        return {key: serialize_for_json(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [serialize_for_json(item) for item in obj]
    else:
        return obj


def make_json_serializable(data):
    """
    Convert data structure to be JSON serializable by handling HttpUrl and other Pydantic types.
    
    Args:
        data: Data structure to make JSON serializable
        
    Returns:
        JSON-serializable version of the data
    """
    return serialize_for_json(data)


# =============================================================================
# Resource Management Utilities  
# =============================================================================

# Global shared Playwright tools instance
_SHARED_PLAYWRIGHT_TOOLS = None

def get_shared_playwright_tools():
    """Get shared Playwright tools to avoid multiple browser instances."""
    global _SHARED_PLAYWRIGHT_TOOLS
    if _SHARED_PLAYWRIGHT_TOOLS is None:
        from src.diligence_agent.mcp_config import get_playwright_tools_with_auth
        _SHARED_PLAYWRIGHT_TOOLS = get_playwright_tools_with_auth()
    return _SHARED_PLAYWRIGHT_TOOLS


# =============================================================================
# Slack Data Utilities
# =============================================================================

def fetch_slack_channel_data(channels: list) -> str:
    """
    Fetch data from multiple Slack channels using MCP tools.
    
    Args:
        channels: List of channel dictionaries with 'name', 'id', and 'description'
        
    Returns:
        Formatted string containing all channel data
    """
    from src.diligence_agent.mcp_config import get_slack_tools
    
    all_slack_content = ""
    slack_tools = get_slack_tools()

    for channel in channels:
        # Add channel header with name and description
        channel_header = f"\n# Channel: {channel['name']}\n"
        channel_header += f"Description: {channel['description']}\n"
        channel_header += f"Channel ID: {channel['id']}\n\n"

        channel_content = ""

        if slack_tools:
            try:
                # Find the slack_get_channel_history tool specifically
                history_tool = None
                for tool in slack_tools:
                    if hasattr(tool, 'name') and tool.name == 'slack_get_channel_history':
                        history_tool = tool
                        break

                if history_tool:
                    # Use the MCP tool to fetch channel messages with correct parameter format
                    result = history_tool._run(
                        channel_id=channel['id'],
                        limit=500
                    )
                    channel_content = f"Messages from {channel['name']}:\n{result}\n"
                else:
                    channel_content = f"slack_get_channel_history tool not found for {channel['name']}\n"

            except Exception as e:
                channel_content = f"Error fetching data from {channel['name']}: {str(e)}\n"
        else:
            channel_content = f"Slack MCP tools not available for {channel['name']}\n"

        # Concatenate channel info with content
        all_slack_content += channel_header + channel_content + "\n"

    return all_slack_content

# =============================================================================
# File Writing Utilities
# =============================================================================

# Define section ordering for consistent numbering
SECTION_ORDER = {
    "Company Overview": 1,
    "Why Interesting": 2, 
    "Product": 3,
    "Competitive Landscape": 4,
    "Market": 5,
    "Founders": 6,
    "Report Conclusion": 7,
    "Final Report": 8,
}

def write_section_file(section_name: str, content: str, company_name: str, current_date: str = "", output_dir: str = "task_outputs") -> str:
    """
    Write a section report to a numbered file with metadata header.
    
    Args:
        section_name: Name of the section
        content: Markdown content to write
        company_name: Company name for directory structure
        current_date: Date when the report was generated
        output_dir: Base output directory
        
    Returns:
        File path where the content was saved
    """
    if not content or not content.strip():
        return ""
    
    # Create company-specific directory
    company_dir = os.path.join(output_dir, company_name)
    os.makedirs(company_dir, exist_ok=True)
    
    # Get section number and format filename
    section_number = SECTION_ORDER.get(section_name, 99)  # Default to 99 for unknown sections
    section_filename = section_name.replace(' ', '_').lower()
    filename = f"{section_number}.{section_filename}.md"
    filepath = os.path.join(company_dir, filename)
    
    # Write file with metadata header and section content
    with open(filepath, 'w', encoding='utf-8') as f:
        # Write metadata header
        
        f.write(f"**Company:** {company_name}  \n")
        f.write(f"**Section:** {section_name}  \n")
        f.write(f"**Generated:** {current_date}  \n")
        
        # Write the actual content
        f.write(content)
    
    return filepath

# =============================================================================
# Other Utilities
# =============================================================================

def join_names_with_and(name_list):
    """
    Joins a list of names with commas, and an 'and' before the last name.
    Handles various list lengths.
    """
    if not name_list:
        return ""
    if len(name_list) == 1:
        return name_list[0]

    # Separate the last element from the rest
    first_part = name_list[:-1]
    last_name = name_list[-1]

    # Join the first part with commas
    comma_separated = ", ".join(first_part)

    # Combine the two parts with " and "
    return f"{comma_separated} and {last_name}"



# Centralized section configuration
from src.diligence_agent.schemas import Founders, CompetitiveLandscape, Market, Product, WhyInteresting, CompanyOverview, ReportConclusion

SECTION_CONFIG = {
    "Founders": {
        "schema": Founders,
        "field": "founders_section"
    },
    "Competitive Landscape": {
        "schema": CompetitiveLandscape,
        "field": "competitive_landscape_section"
    },
    "Market": {
        "schema": Market,
        "field": "market_section"
    },
    "Product": {
        "schema": Product,
        "field": "product_section"
    },
    "Why Interesting": {
        "schema": WhyInteresting,
        "field": "why_interesting_section"
    },
    "Company Overview": {
        "schema": CompanyOverview,
        "field": "company_overview_section"
    },
    "Report Conclusion": {
        "schema": ReportConclusion,
        "field": "report_conclusion_section"
    },
}

def get_schema_for_section(section: str) -> Type[BaseModel]:
    """Get schema class for dynamic schema selection without global state."""
    config = SECTION_CONFIG.get(section)
    if not config:
        raise ValueError(f"Unknown section: {section}")
    return config["schema"]

def get_field_for_section(section: str) -> str:
    """Get report structure field name for a section."""
    config = SECTION_CONFIG.get(section)
    if not config:
        raise ValueError(f"Unknown section: {section}")
    return config["field"]  
