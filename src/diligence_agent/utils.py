"""
Utility functions for the diligence agent.
"""

import asyncio
import json
import re
from typing import List, Any, Coroutine, Type, Optional
from pydantic import BaseModel


# =============================================================================
# Async Execution Utilities
# =============================================================================

async def execute_coroutines(coroutines: List[Coroutine], parallel: bool = True) -> List[Any]:
    """
    Execute a list of coroutines either in parallel or sequentially with unified tracing.
    
    This function ensures all executions appear under the same trace hierarchy:
    - Parallel: Uses asyncio.gather() which preserves context via contextvars
    - Sequential: Executes with explicit trace context propagation for unified Opik tracing
    
    Args:
        coroutines: List of coroutines to execute
        parallel: If True, run in parallel; if False, run sequentially
        
    Returns:
        List of results in the same order as input coroutines
    """
    if parallel:
        # asyncio.gather automatically propagates context to each coroutine
        return await asyncio.gather(*coroutines)
    else:
        # Sequential execution with unified tracing context
        results = []
        
        # Sequential execution with standard async context propagation
        # Context variables and asyncio naturally propagate context in sequential execution
        for i, coro in enumerate(coroutines):
            print(f"Executing SubFlow {i+1} sequentially...")
            result = await coro
            results.append(result)
        
        return results


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
        
    Raises:
        ValueError: If extraction and parsing fails
    """
    # First try: if pydantic object exists and schema is requested, use it
    if target_schema and hasattr(result, 'pydantic') and result.pydantic:
        return result.pydantic
    
    # Second try: extract raw output and clean it
    raw_output = result.raw if hasattr(result, 'raw') else str(result)
    
    # Remove markdown code blocks (```json at start, ``` at end)
    cleaned = re.sub(r'^```json\s*\n?', '', raw_output.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r'\n?```\s*$', '', cleaned, flags=re.MULTILINE)
    
    # Extract only JSON content within curly brackets
    json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if json_match:
        cleaned = json_match.group(0)
    
    cleaned = cleaned.strip()
    
    try:
        parsed_data = json.loads(cleaned)
        if target_schema:
            return target_schema(**parsed_data)
        else:
            return parsed_data
    except json.JSONDecodeError as e:
        schema_name = target_schema.__name__ if target_schema else "JSON"
        raise ValueError(f"Could not parse JSON for {schema_name}: {e}")
    except Exception as e:
        schema_name = target_schema.__name__ if target_schema else "JSON"
        raise ValueError(f"Could not validate {schema_name} schema: {e}")


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