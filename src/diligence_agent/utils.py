"""
Utility functions for the diligence agent.
"""

import asyncio
import json
import os
import re
from typing import List, Any, Coroutine, Type, Optional, Dict
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
    current_date: str = "",
    batch_size: int = 2,
    batch_delay: float = 0.0
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


def _convert_markdown_to_google_docs_format(markdown_content: str) -> List[Dict]:
    """Convert markdown content to Google Docs API format requests."""
    requests = []
    
    # Split content by lines and filter out empty lines
    lines = [line for line in markdown_content.split('\n') if line.strip()]
    current_index = 1  # Start after the initial paragraph
    
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
            # Bullet points
            clean_text = line[2:] + '\n'
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': clean_text
                }
            })
            requests.append({
                'createParagraphBullets': {
                    'range': {
                        'startIndex': current_index,
                        'endIndex': current_index + len(clean_text) - 1
                    },
                    'bulletPreset': 'BULLET_DISC_CIRCLE_SQUARE'
                }
            })
            current_index += len(clean_text)
            
        else:
            # Regular paragraph - handle bold text **text**
            processed_text = line
            bold_ranges = []
            
            # Find bold text patterns - handles both inline and beginning-of-line bold
            bold_pattern = r'\*\*(.*?)\*\*'
            matches = list(re.finditer(bold_pattern, processed_text))
            
            # Process matches in reverse order to maintain correct indices
            for match in reversed(matches):
                start_pos_in_processed = match.start()
                end_pos_in_processed = match.start() + len(match.group(1))
                bold_ranges.append((current_index + start_pos_in_processed, current_index + end_pos_in_processed))
                # Replace **content** with just content
                processed_text = processed_text[:match.start()] + match.group(1) + processed_text[match.end():]
            
            text_with_newline = processed_text + '\n'
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': text_with_newline
                }
            })
            
            # Apply bold formatting
            for start_idx, end_idx in bold_ranges:
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
        
        # Add timestamp to document name to prevent duplicates
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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
        return None
