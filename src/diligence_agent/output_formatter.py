"""
Simple deterministic JSON cleaner for LLM outputs.
Handles CrewAI result objects and cleans markdown-wrapped JSON.
"""

import re
import json
from typing import Type, Any
from pydantic import BaseModel


def extract_structured_output(result: Any, target_schema: Type[BaseModel]) -> BaseModel:
    """
    Extract structured output from CrewAI result, cleaning if necessary.
    
    Args:
        result: CrewAI agent result object
        target_schema: Pydantic model to validate against
        
    Returns:
        Validated instance of target_schema
        
    Raises:
        ValueError: If extraction and parsing fails
    """
    # First try: if pydantic object exists, use it
    if hasattr(result, 'pydantic') and result.pydantic:
        return result.pydantic
    
    # Second try: extract raw output and clean it
    raw_output = result.raw if hasattr(result, 'raw') else str(result)
    
    # Remove markdown code blocks (```json at start, ``` at end)
    cleaned = re.sub(r'^```json\s*\n?', '', raw_output.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r'\n?```\s*$', '', cleaned, flags=re.MULTILINE)
    cleaned = cleaned.strip()
    
    try:
        parsed_data = json.loads(cleaned)
        return target_schema(**parsed_data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Could not parse JSON for {target_schema.__name__}: {e}")
    except Exception as e:
        raise ValueError(f"Could not validate {target_schema.__name__} schema: {e}")