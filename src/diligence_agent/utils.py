"""
Utility functions for the diligence agent.
"""

import asyncio
import json
import os
import re
from typing import List, Any, Coroutine, Type, Optional, Dict, Callable
from pydantic import BaseModel


# =============================================================================
# Cost Tracking Utilities
# =============================================================================

class CostTracker:
    """Track token usage, costs, and LLM calls across agent executions"""

    def __init__(self):
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_cost = 0.0
        self.total_llm_calls = 0
        self.model = None

    def track_usage(self, result, model: str = None):
        """Track token usage and cost from CrewAI agent results"""
        if model:
            self.model = model

        # Count every LLM call
        self.total_llm_calls += 1

        # Initialize variables
        tokens = 0
        prompt_tokens = 0
        completion_tokens = 0
        cost = 0.0

        # Check for usage_metrics (it's a dictionary in CrewAI LiteAgentOutput)
        if hasattr(result, 'usage_metrics') and result.usage_metrics:
            usage_dict = result.usage_metrics

            # Extract token information from dictionary
            if 'total_tokens' in usage_dict and usage_dict['total_tokens']:
                tokens = usage_dict['total_tokens']
                self.total_tokens += tokens

            # Track prompt and completion tokens separately if available
            if 'prompt_tokens' in usage_dict and usage_dict['prompt_tokens']:
                prompt_tokens = usage_dict['prompt_tokens']
                self.prompt_tokens += prompt_tokens
            if 'completion_tokens' in usage_dict and usage_dict['completion_tokens']:
                completion_tokens = usage_dict['completion_tokens']
                self.completion_tokens += completion_tokens

            # Get actual cost if available from LiteLLM or OpenAI response
            cost = 0.0
            if 'completion_cost' in usage_dict and usage_dict['completion_cost']:
                cost = float(usage_dict['completion_cost'])
            elif 'total_cost' in usage_dict and usage_dict['total_cost']:
                cost = float(usage_dict['total_cost'])
            elif model and tokens:
                # Calculate estimated cost based on known pricing
                cost = self._estimate_cost(model, prompt_tokens, completion_tokens)

            print("Usage Metrics:", result.usage_metrics)

            if cost > 0:
                self.total_cost += cost
                print(f"💰 Call #{self.total_llm_calls} | Tokens: {tokens:,} | Cost: ${cost:.4f} | Total: {self.total_tokens:,} tokens, ${self.total_cost:.4f}")
            else:
                print(f"💰 Call #{self.total_llm_calls} | Tokens: {tokens:,} | Total: {self.total_tokens:,} tokens")
        else:
            print(f"💰 Call #{self.total_llm_calls} | No usage data available in result object")

    def _estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate cost based on model pricing (fallback when actual cost unavailable)"""
        model_lower = model.lower()

        # OpenAI pricing per 1K tokens (as of 2024/2025)
        pricing = {
            'gpt-4o': {'prompt': 0.0025, 'completion': 0.01},
            'gpt-4o-mini': {'prompt': 0.00015, 'completion': 0.0006},
            'gpt-4.1': {'prompt': 0.003, 'completion': 0.012},
            'gpt-4.1-mini': {'prompt': 0.00015, 'completion': 0.0006},
            'gpt-4': {'prompt': 0.003, 'completion': 0.006},
            'gpt-3.5-turbo': {'prompt': 0.0005, 'completion': 0.0015}
        }

        # Find matching pricing
        model_pricing = None
        for model_name, prices in pricing.items():
            if model_name in model_lower:
                model_pricing = prices
                break

        if not model_pricing:
            # Default fallback pricing
            model_pricing = {'prompt': 0.0015, 'completion': 0.002}

        prompt_cost = (prompt_tokens / 1000) * model_pricing['prompt']
        completion_cost = (completion_tokens / 1000) * model_pricing['completion']

        return prompt_cost + completion_cost

    def get_summary(self) -> Dict[str, Any]:
        """Get cost and usage summary"""
        return {
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_cost": self.total_cost,
            "total_llm_calls": self.total_llm_calls,
            "model": self.model
        }

    def reset(self):
        """Reset tracking counters"""
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_cost = 0.0
        self.total_llm_calls = 0


# Global cost tracker instance
_global_cost_tracker = CostTracker()

def get_global_cost_tracker() -> CostTracker:
    """Get the global cost tracker instance"""
    return _global_cost_tracker

def reset_global_cost_tracker():
    """Reset the global cost tracker"""
    _global_cost_tracker.reset()


# =============================================================================
# Async Execution Utilities
# =============================================================================

async def execute_subflows_and_map_results(
    subflow_class,
    sections: List[str],
    base_inputs: dict,
    report_structure,
    company_name: str = "",
    current_date: str = "",
    batch_size: int = 2,
    batch_delay: float = 0.0,
    progress_callback: Optional[Callable[[str, str], None]] = None
) -> Any:
    """
    Execute multiple subflows in batches and map results to report structure fields.
    
    Args:
        subflow_class: The Flow class to instantiate for each section
        sections: List of section names to process
        base_inputs: Common inputs for all subflows
        report_structure: Report structure object to update
        company_name: Company name for file naming
        current_date: Date when the report was generated
        batch_size: Number of sections to run in parallel per batch
        batch_delay: Delay in seconds between batches
        
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

    # Execute subflows in batches
    results = []
    for i in range(0, len(coroutines), batch_size):
        batch = coroutines[i:i+batch_size]
        batch_sections = sections[i:i+batch_size]
        
        print(f"Starting batch {i//batch_size + 1}: {', '.join(batch_sections)}")
        batch_results = await asyncio.gather(*batch)
        results.extend(batch_results)
        
        # Add delay between batches if specified and not the last batch
        if batch_delay > 0 and i + batch_size < len(coroutines):
            print(f"Waiting {batch_delay} seconds before next batch...")
            await asyncio.sleep(batch_delay)

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
        print("🧹 clean_markdown_output: No content to clean")
        return content
    
    print(f"🧹 clean_markdown_output: Cleaning content (length: {len(content)} chars)")
    print(f"🧹 Content preview: {content[:200]}...")
    
    # Remove markdown code blocks (```markdown at start, ``` at end)
    cleaned = re.sub(r'^```markdown\s*\n?', '', content.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r'\n?```\s*$', '', cleaned, flags=re.MULTILINE)
    
    # Remove horizontal rules (--- or ***) 
    cleaned = re.sub(r'^[-*]{3,}\s*$', '', cleaned, flags=re.MULTILINE)
    
    # Clean up extra blank lines that may result from removing horizontal rules
    cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)
    
    result = cleaned.strip()
    print(f"🧹 clean_markdown_output: Result length: {len(result)} chars")
    
    return result

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
        from diligence_agent.mcp_config import get_playwright_tools_with_auth
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
    from diligence_agent.mcp_config import get_slack_tools
    
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
                    # Reduced limit to prevent timeouts with large channels
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

def write_parsed_data_sources(parsed_sources: Dict[str, str], company_name: str, current_date: str = "", output_dir: str = "task_outputs") -> None:
    """Write parsed data sources to individual files."""
    for source_name, markdown_content in parsed_sources.items():
        # Clean source name for filename
        safe_filename = source_name.replace(":", "").replace("/", "_").replace(" ", "_")
        write_section_file(f"Data_Source_{safe_filename}", markdown_content, company_name, current_date, output_dir, skip_numbering=True)

def write_section_file(section_name: str, content: str, company_name: str, current_date: str = "", output_dir: str = "task_outputs", skip_numbering: bool = False) -> str:
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
    try:
        if not content or not content.strip():
            print(f"⚠️  No content to write for section: {section_name}")
            return ""
        
        print(f"📝 Writing section: {section_name} (content length: {len(content)} chars)")
        
        # Create company-specific directory
        company_dir = os.path.join(output_dir, company_name)
        os.makedirs(company_dir, exist_ok=True)
        print(f"📁 Using directory: {company_dir}")
        
        # Format filename with or without numbering
        section_filename = section_name.replace(' ', '_').lower()
        if skip_numbering:
            filename = f"{section_filename}.md"
        else:
            section_number = SECTION_ORDER.get(section_name, 99)  # Default to 99 for unknown sections
            filename = f"{section_number}.{section_filename}.md"
        filepath = os.path.join(company_dir, filename)
        print(f"💾 Writing to: {filepath}")
        
        # Write file with metadata header and section content
        with open(filepath, 'w', encoding='utf-8') as f:
            # Write metadata header
            f.write(f"**Company:** {company_name}  \n")
            f.write(f"**Section:** {section_name}  \n")
            f.write(f"**Generated:** {current_date}  \n\n")
            
            # Write the actual content
            f.write(content)
        
        print(f"✅ Successfully wrote {filepath}")
        return filepath
        
    except Exception as e:
        print(f"❌ Error writing section {section_name}: {str(e)}")
        import traceback
        traceback.print_exc()
        return ""

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
from diligence_agent.schemas import Founders, CompetitiveLandscape, Market, Product, WhyInteresting, CompanyOverview, ReportConclusion

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


def _convert_markdown_to_google_docs_format(markdown_content: str) -> List[Dict]:
    """Convert markdown content to Google Docs API format requests."""
    requests = []
    
    # Split content by lines and filter out empty lines
    lines = [line for line in markdown_content.split('\n') if line.strip()]
    current_index = 1  # Start after the initial paragraph
    
    def _add_paragraph_spacing(start_idx: int, end_idx: int):
        """Add space after paragraph for better readability."""
        return {
            'updateParagraphStyle': {
                'range': {
                    'startIndex': start_idx,
                    'endIndex': end_idx
                },
                'paragraphStyle': {
                    'spaceAfter': {
                        'magnitude': 6,
                        'unit': 'PT'
                    }
                },
                'fields': 'spaceAfter'
            }
        }
    
    for line in lines:
        line = line.strip()
        
        # Process different markdown elements
        if line.startswith('# '):
            # H1 - Title style
            clean_text = line[2:] + '\n'
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': clean_text
                }
            })
            requests.append({
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': current_index,
                        'endIndex': current_index + len(clean_text) - 1
                    },
                    'paragraphStyle': {
                        'namedStyleType': 'TITLE'
                    },
                    'fields': 'namedStyleType'
                }
            })
            current_index += len(clean_text)
            
        elif line.startswith('## '):
            # H2 - Heading 1 style
            clean_text = line[3:] + '\n'
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': clean_text
                }
            })
            requests.append({
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': current_index,
                        'endIndex': current_index + len(clean_text) - 1
                    },
                    'paragraphStyle': {
                        'namedStyleType': 'HEADING_1'
                    },
                    'fields': 'namedStyleType'
                }
            })
            current_index += len(clean_text)
            
        elif line.startswith('### '):
            # H3 - Heading 2 style
            clean_text = line[4:] + '\n'
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': clean_text
                }
            })
            requests.append({
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': current_index,
                        'endIndex': current_index + len(clean_text) - 1
                    },
                    'paragraphStyle': {
                        'namedStyleType': 'HEADING_2'
                    },
                    'fields': 'namedStyleType'
                }
            })
            current_index += len(clean_text)
            
        elif line.startswith('- ') or line.startswith('* '):
            # Bullet points - handle bold text **text**
            processed_text = line[2:]
            bold_ranges = []
            
            # Find bold text patterns
            bold_pattern = r'\*\*(.*?)\*\*'
            matches = list(re.finditer(bold_pattern, processed_text))
            
            # Calculate positions in the final text (after ** removal)
            offset = 0
            for match in matches:
                start_in_original = match.start()
                content = match.group(1)
                start_in_processed = start_in_original - offset
                end_in_processed = start_in_processed + len(content)
                bold_ranges.append((current_index + start_in_processed, current_index + end_in_processed))
                processed_text = processed_text[:start_in_original - offset] + content + processed_text[start_in_original - offset + len(match.group(0)):]
                offset += 4
            
            text_with_newline = processed_text + '\n'
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': text_with_newline
                }
            })
            requests.append({
                'createParagraphBullets': {
                    'range': {
                        'startIndex': current_index,
                        'endIndex': current_index + len(text_with_newline) - 1
                    },
                    'bulletPreset': 'BULLET_DISC_CIRCLE_SQUARE'
                }
            })
            
            # Apply bold formatting
            for start_idx, end_idx in reversed(bold_ranges):
                requests.append({
                    'updateTextStyle': {
                        'range': {
                            'startIndex': start_idx,
                            'endIndex': end_idx
                        },
                        'textStyle': {
                            'bold': True
                        },
                        'fields': 'bold'
                    }
                })
            
            current_index += len(text_with_newline)
            
        elif re.match(r'^\d+\.\s+', line):
            # Numbered lists - handle bold text **text**
            processed_text = line
            bold_ranges = []
            
            # Find bold text patterns
            bold_pattern = r'\*\*(.*?)\*\*'
            matches = list(re.finditer(bold_pattern, processed_text))
            
            # Calculate positions in the final text (after ** removal)
            offset = 0
            for match in matches:
                start_in_original = match.start()
                content = match.group(1)
                start_in_processed = start_in_original - offset
                end_in_processed = start_in_processed + len(content)
                bold_ranges.append((current_index + start_in_processed, current_index + end_in_processed))
                processed_text = processed_text[:start_in_original - offset] + content + processed_text[start_in_original - offset + len(match.group(0)):]
                offset += 4
            
            text_with_newline = processed_text + '\n'
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': text_with_newline
                }
            })
            
            # Apply bold formatting
            for start_idx, end_idx in reversed(bold_ranges):
                requests.append({
                    'updateTextStyle': {
                        'range': {
                            'startIndex': start_idx,
                            'endIndex': end_idx
                        },
                        'textStyle': {
                            'bold': True
                        },
                        'fields': 'bold'
                    }
                })
            
            current_index += len(text_with_newline)
            
        else:
            # Regular paragraph - handle bold text **text**
            processed_text = line
            bold_ranges = []
            
            # Find bold text patterns - handles both inline and beginning-of-line bold
            bold_pattern = r'\*\*(.*?)\*\*'
            matches = list(re.finditer(bold_pattern, line))
            
            # Calculate positions in the final text (after ** removal)
            offset = 0
            for match in matches:
                # Position in original text
                start_in_original = match.start()
                content = match.group(1)
                
                # Position in processed text (accounting for previous ** removals)
                start_in_processed = start_in_original - offset
                end_in_processed = start_in_processed + len(content)
                
                # Store range for formatting (relative to current_index)
                bold_ranges.append((current_index + start_in_processed, current_index + end_in_processed))
                
                # Remove the ** markers
                processed_text = processed_text[:start_in_original - offset] + content + processed_text[start_in_original - offset + len(match.group(0)):]
                offset += 4  # Each ** pair removed = 4 characters
            
            text_with_newline = processed_text + '\n'
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': text_with_newline
                }
            })
            
            # Add paragraph spacing for regular paragraphs
            requests.append({
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': current_index,
                        'endIndex': current_index + len(text_with_newline) - 1
                    },
                    'paragraphStyle': {
                        'spaceAbove': {
                            'magnitude': 0,
                            'unit': 'PT'
                        },
                        'spaceBelow': {
                            'magnitude': 6,
                            'unit': 'PT'
                        }
                    },
                    'fields': 'spaceAbove,spaceBelow'
                }
            })
            
            # Apply bold formatting - reverse order to apply from end to start
            for start_idx, end_idx in reversed(bold_ranges):
                requests.append({
                    'updateTextStyle': {
                        'range': {
                            'startIndex': start_idx,
                            'endIndex': end_idx
                        },
                        'textStyle': {
                            'bold': True
                        },
                        'fields': 'bold'
                    }
                })
            
            current_index += len(text_with_newline)
    
    return requests


def write_final_report_to_google_doc(document_name: str, markdown_content: str, source_doc_url: str) -> Optional[str]:
    """
    Write final report to Google Drive as a formatted Google Doc.
    
    Args:
        document_name: Name for the new Google Doc
        markdown_content: Markdown content to convert and write
        source_doc_url: Source Google Doc URL to extract folder from
        
    Returns:
        Google Doc URL if successful, None if failed
    """
    try:
        from .tools.google_doc_processor import GoogleDocProcessor
        import os
        from datetime import datetime
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        
        # Add readable timestamp to document name
        timestamp = datetime.now().strftime("%Y-%m-%d_%I:%M:%S%p").lower()
        timestamped_name = f"{document_name}_{timestamp}"
        
        print(f"📄 Creating Google Doc: {timestamped_name}")
        
        # Reuse GoogleDocProcessor's authentication logic
        processor = GoogleDocProcessor()
        
        # Get authenticated services
        client_id = os.getenv('GOOGLE_CLIENT_ID', '').strip()
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET', '').strip()
        refresh_token = os.getenv('GOOGLE_REFRESH_TOKEN', '').strip()
        
        if not all([client_id, client_secret, refresh_token]):
            raise ValueError("Missing Google OAuth2 credentials")
        
        # Create credentials with minimal scopes (same as GoogleDocProcessor)
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret
            # Let Google determine scopes from the existing token
        )
        
        if not creds.valid:
            creds.refresh(Request())
        
        docs_service = build('docs', 'v1', credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)
        
        # Extract folder from source doc
        doc_info = processor._extract_document_id_and_type(source_doc_url)
        folder_id = None
        
        if doc_info and doc_info[0]:
            doc_id = doc_info[0]
            try:
                file_info = drive_service.files().get(fileId=doc_id, fields='parents').execute()
                parents = file_info.get('parents', [])
                if parents:
                    folder_id = parents[0]
                    print(f"📁 Found folder ID: {folder_id}")
            except Exception as e:
                print(f"⚠️ Could not get folder info: {e}")
        else:
            print("⚠️ Could not extract document ID from source URL")
        
        # Create document (first create it, then move to folder)
        doc = docs_service.documents().create(body={'title': timestamped_name}).execute()
        document_id = doc.get('documentId')
        document_url = f"https://docs.google.com/document/d/{document_id}/edit"
        
        print(f"📄 Created Google Doc: {timestamped_name}")
        
        # Move document to the correct folder if we found one
        if folder_id:
            try:
                # Move the document to the target folder
                drive_service.files().update(
                    fileId=document_id,
                    addParents=folder_id,
                    removeParents='root'  # Remove from root folder
                ).execute()
                print(f"📁 Moved document to folder: {folder_id}")
            except Exception as e:
                print(f"⚠️ Could not move document to folder: {e}")
        
        # Convert markdown to Google Docs formatting
        print("📝 Converting markdown to Google Docs format...")
        formatting_requests = _convert_markdown_to_google_docs_format(markdown_content)
        
        if formatting_requests:
            docs_service.documents().batchUpdate(
                documentId=document_id,
                body={'requests': formatting_requests}
            ).execute()
            print("✅ Applied Google Docs formatting")
        
        print(f"✅ Google Doc created successfully: {document_url}")
        return document_url
        
    except Exception as e:
        print(f"⚠️ Warning: Could not create Google Doc: {str(e)}")
        print("   Local file output has been preserved")


# =============================================================================
# Company Sources Parsing (Deterministic)
# =============================================================================

def parse_all_companies_from_sources():
    """
    Parse all companies from the master diligence sources document using deterministic regex parsing.
    
    Returns:
        Dictionary mapping company names to their DataSources
        
    Raises:
        Exception: If the sources document URL is not configured or parsing fails
    """
    from diligence_agent.tools.google_doc_processor import GoogleDocProcessor
    from diligence_agent.schemas import DataSources
    
    # Get the sources document URL from environment
    sources_doc_url = os.getenv("DILIGENCE_SOURCES_DOC_URL")
    if not sources_doc_url:
        raise Exception(
            "DILIGENCE_SOURCES_DOC_URL environment variable not set. "
            "Please set it to the URL of your master diligence sources Google Doc."
        )
    
    try:
        # Get raw content from Google Doc
        print("📄 Fetching companies data from sources document...")
        google_doc_processor = GoogleDocProcessor()
        raw_content = google_doc_processor._run(sources_doc_url).strip()
        
        if not raw_content:
            raise Exception("Sources document appears to be empty")
        
        # Parse the document deterministically
        print("🔍 Parsing company data sources...")
        companies_dict = _parse_company_sources_content(raw_content)
        
        print(f"✅ Successfully parsed {len(companies_dict)} companies from sources document")
        
        # Log company names found
        for company_name in companies_dict.keys():
            print(f"   • {company_name}")
        
        return companies_dict
        
    except Exception as e:
        error_msg = f"Failed to parse companies from sources document: {str(e)}"
        print(f"❌ {error_msg}")
        raise Exception(error_msg)


def _parse_company_sources_content(content: str) -> Dict[str, "DataSources"]:
    """
    Parse the raw content of the sources document using regex patterns.
    
    Args:
        content: Raw text content from the Google Doc
        
    Returns:
        Dictionary mapping company names to DataSources objects
    """
    from diligence_agent.schemas import DataSources
    
    companies = {}
    
    # Split content into lines and clean them
    lines = [line.strip() for line in content.split('\n')]
    
    current_company = None
    current_section = None
    current_items = []
    
    # Regex patterns
    company_pattern = re.compile(r'^Company(?:\s+name)?:\s*(.+?)$', re.IGNORECASE)
    section_patterns = {
        'google_docs': re.compile(r'^Google\s+docs?:?\s*$', re.IGNORECASE),
        'websites': re.compile(r'^Websites?:?\s*$', re.IGNORECASE),
        'pdfs': re.compile(r'^PDFs?:?\s*$', re.IGNORECASE),
        'slack_channels': re.compile(r'^Slack\s+(?:channels?|channel):?\s*$', re.IGNORECASE)
    }
    bullet_pattern = re.compile(r'^[•·\-\*]\s*(.+)$')
    # Also capture non-bullet content under sections (for items that don't have bullets)
    content_pattern = re.compile(r'^(.+)$')
    
    def finalize_section():
        """Add current section items to the current company"""
        if current_company and current_section and current_items:
            if current_company not in companies:
                companies[current_company] = DataSources()
            
            # Set the items for the current section
            setattr(companies[current_company], current_section, current_items.copy())
            current_items.clear()
    
    # Process each line
    for line in lines:
        if not line:
            continue
            
        # Check for company name
        company_match = company_pattern.match(line)
        if company_match:
            # Finalize previous section before starting new company
            finalize_section()
            current_company = company_match.group(1).strip()
            current_section = None
            continue
        
        # Check for section headers
        section_found = False
        for section_name, pattern in section_patterns.items():
            if pattern.match(line):
                # Finalize previous section before starting new one
                finalize_section()
                current_section = section_name
                section_found = True
                break
        
        if section_found:
            continue
        
        # Check for bullet point items first
        bullet_match = bullet_pattern.match(line)
        if bullet_match and current_section:
            item = bullet_match.group(1).strip()
            if item:
                # Clean up the item (remove extra formatting, brackets, etc.)
                item = _clean_source_item(item, current_section)
                if item:
                    current_items.append(item)
        elif current_section and line.strip():
            # If we're in a section and this line doesn't start another company or section,
            # treat it as content for the current section (for lines without bullets)
            item = line.strip()
            if item:
                # Clean up the item
                item = _clean_source_item(item, current_section)
                if item:
                    current_items.append(item)
    
    # Finalize the last section
    finalize_section()
    
    return companies


def _clean_source_item(item: str, section_type: str) -> str:
    """
    Clean up a source item based on its type.
    
    Args:
        item: Raw item text
        section_type: Type of section (google_docs, websites, pdfs, slack_channels)
        
    Returns:
        Cleaned item text
    """
    # Extract URL from square brackets at the end (e.g., "Title [https://url]")
    url_match = re.search(r'\[https?://[^\]]+\]$', item)
    if url_match:
        # Extract the URL without brackets
        return url_match.group(0)[1:-1]  # Remove [ and ]
    
    # Remove common prefixes and formatting
    item = re.sub(r'^\[.*?\]\s*', '', item)  # Remove [TensorStax] style prefixes
    item = re.sub(r'^https?://', 'https://', item)  # Normalize URLs
    
    if section_type == 'google_docs':
        # For Google Docs, if it looks like a title, we might need to reconstruct the URL
        # For now, just clean the title
        if not item.startswith('http'):
            # This is a doc title, keep it as is for now
            # In a real implementation, you might want to maintain a mapping of titles to URLs
            pass
    elif section_type == 'websites':
        # Ensure websites have proper URL format
        if not item.startswith('http') and '.' in item:
            item = f'https://{item}'
    elif section_type == 'pdfs':
        # PDFs might be filenames or URLs
        pass
    elif section_type == 'slack_channels':
        # Slack channels should be channel IDs
        # Extract channel ID from full Slack URL or return as-is if already an ID
        slack_url_match = re.search(r'https?://[^/]*\.slack\.com/.*?/([A-Z0-9]{9,11})', item)
        if slack_url_match:
            # Extract channel ID from URL (format: https://company.slack.com/.../C1234567890/...)
            item = slack_url_match.group(1)
        else:
            # Remove # prefix if present (for channel names or IDs)
            item = re.sub(r'^#', '', item)
    
    return item.strip()


def get_available_companies() -> List[str]:
    """
    Get list of available company names from the sources document.
    
    Returns:
        List of company names, or empty list if parsing fails
    """
    try:
        companies_dict = parse_all_companies_from_sources()
        return list(companies_dict.keys())
    except Exception as e:
        print(f"⚠️ Warning: Could not get available companies: {e}")
        return []


def get_company_data_sources(company_name: str):
    """
    Get data sources for a specific company.
    Performs case-insensitive matching.
    
    Args:
        company_name: Name of the company to get data sources for
        
    Returns:
        DataSources object for the company, or None if not found
    """
    try:
        companies_dict = parse_all_companies_from_sources()
        
        # Case-insensitive search
        company_name_lower = company_name.lower().strip()
        for available_name, data_sources in companies_dict.items():
            if available_name.lower().strip() == company_name_lower:
                return data_sources
        
        return None
    except Exception as e:
        print(f"⚠️ Warning: Could not get data sources for {company_name}: {e}")
        return None


def validate_company_name(company_name: str) -> tuple[bool, Optional[str], List[str]]:
    """
    Validate if a company name exists in the sources document.
    
    Args:
        company_name: Name to validate
        
    Returns:
        Tuple of (is_valid, matched_name, available_companies)
    """
    try:
        available_companies = get_available_companies()
        
        if not available_companies:
            return False, None, []
        
        # Case-insensitive search
        company_name_lower = company_name.lower().strip()
        for available_name in available_companies:
            if available_name.lower().strip() == company_name_lower:
                return True, available_name, available_companies
        
        return False, None, available_companies
    except Exception as e:
        print(f"⚠️ Warning: Could not validate company name: {e}")
        return False, None, []
