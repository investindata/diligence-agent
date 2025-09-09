"""
Simple deterministic JSON cleaner for LLM outputs.
Handles CrewAI result objects and cleans markdown-wrapped JSON.
"""

import re
import json
from typing import Type, Any
from pydantic import BaseModel


def extract_structured_output(result: Any, target_schema: Type[BaseModel] = None):
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