from crewai.tools import BaseTool
from typing import Type, Optional
from pydantic import BaseModel, Field
import re
import requests
import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleDocProcessorInput(BaseModel):
    """Input schema for GoogleDocProcessor."""
    google_doc_url: str = Field(..., description="The URL of the Google Doc to process.")

class GoogleDocProcessor(BaseTool):
    name: str = "Google Doc Processor"
    description: str = (
        "Process a Google Doc and return the content as a string. "
        "Supports both public documents and private documents via OAuth2 authentication."
    )
    args_schema: Type[BaseModel] = GoogleDocProcessorInput

    def _get_authenticated_service(self, service_name: str, version: str):
        """Get authenticated Google API service"""
        # Check for OAuth2 credentials in environment
        client_id = os.getenv('GOOGLE_CLIENT_ID', '').strip()
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET', '').strip()
        refresh_token = os.getenv('GOOGLE_REFRESH_TOKEN', '').strip()
        
        if not all([client_id, client_secret, refresh_token]):
            return None  # Fall back to unauthenticated access
        
        try:
            # Create credentials from environment variables
            creds = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret
            )
            
            # Refresh the token if needed
            if not creds.valid:
                creds.refresh(Request())
            
            # Build and return the service
            return build(service_name, version, credentials=creds)
            
        except Exception as e:
            print(f"Warning: Failed to authenticate with Google API: {e}")
            return None  # Fall back to unauthenticated access

    def _run(self, google_doc_url: str) -> str:
        document_id, doc_type = self._extract_document_id_and_type(google_doc_url)
        if document_id is None or doc_type is None:
            raise ValueError("Could not extract Google Doc/Sheet ID and type from the provided URL.")

        # Try authenticated access first
        auth_content = self._try_authenticated_access(document_id, doc_type)
        if auth_content:
            return auth_content
        
        # Fall back to public access
        print("Attempting unauthenticated access (document must be publicly accessible)")
        return self._try_public_access(document_id, doc_type)

    def _try_authenticated_access(self, document_id: str, doc_type: str) -> Optional[str]:
        """Try to access document using authenticated Google API"""
        try:
            if doc_type == "document":
                # Use Google Docs API
                service = self._get_authenticated_service('docs', 'v1')
                if not service:
                    return None
                
                doc = service.documents().get(documentId=document_id).execute()
                content = self._extract_text_from_doc_structure(doc)
                print(f"✅ Successfully accessed document via Google Docs API")
                return content
                
            elif doc_type == "spreadsheets":
                # Use Google Sheets API
                service = self._get_authenticated_service('sheets', 'v4')
                if not service:
                    return None
                
                sheet = service.spreadsheets().get(spreadsheetId=document_id).execute()
                content = self._extract_text_from_sheet_structure(sheet, service, document_id)
                print(f"✅ Successfully accessed spreadsheet via Google Sheets API")
                return content
                
        except HttpError as e:
            if e.resp.status == 403:
                print("Access denied - document is not shared with your Google account")
            else:
                print(f"Google API error: {e}")
        except Exception as e:
            print(f"Authentication failed: {e}")
        
        return None

    def _try_public_access(self, document_id: str, doc_type: str) -> str:
        """Fall back to public export URLs (original method)"""
        if doc_type == "document":
            export_urls = [
                f"https://docs.google.com/document/d/{document_id}/export?format=txt",
                f"https://docs.google.com/document/d/{document_id}/export?format=html",
            ]
        elif doc_type == "spreadsheets":
            export_urls = [
                f"https://docs.google.com/spreadsheets/d/{document_id}/export?format=csv",
                f"https://docs.google.com/spreadsheets/d/{document_id}/export?format=tsv",
            ]
        else:
            raise ValueError("Unsupported Google file type.")

        last_error: Optional[str] = None
        for export_url in export_urls:
            try:
                response = requests.get(export_url, timeout=30)
                if response.status_code == 200:
                    text = response.text
                    # For HTML, do a very light tag strip fallback
                    if "<html" in text.lower():
                        text = re.sub(r"<[^>]+>", "\n", text)
                        text = re.sub(r"\n{2,}", "\n\n", text).strip()
                    print(f"✅ Successfully accessed document via public export")
                    return text.strip()
                else:
                    last_error = f"HTTP {response.status_code} for {export_url}"
            except Exception as exc:
                last_error = str(exc)

        raise RuntimeError(
            "Failed to fetch Google Doc/Sheet content using both authenticated and public access. "
            "For private documents, ensure OAuth2 is set up correctly. "
            "For public access, ensure the document is shared as 'Anyone with the link'. "
            f"Last error: {last_error or 'unknown'}"
        )

    def _extract_text_from_doc_structure(self, doc: dict) -> str:
        """Extract text from Google Docs API response structure"""
        content = doc.get('body', {}).get('content', [])
        text_parts = []
        
        for element in content:
            if 'paragraph' in element:
                paragraph = element['paragraph']
                if 'elements' in paragraph:
                    for elem in paragraph['elements']:
                        if 'textRun' in elem:
                            text_run = elem['textRun']
                            content_text = text_run.get('content', '')
                            
                            # Check if this text run has a hyperlink
                            text_style = text_run.get('textStyle', {})
                            if 'link' in text_style and 'url' in text_style['link']:
                                # Add both the display text and the actual URL
                                url = text_style['link']['url']
                                text_parts.append(f"{content_text} [{url}]")
                            else:
                                text_parts.append(content_text)
                        elif 'richLink' in elem:
                            rich_link = elem['richLink']
                            
                            # Extract URL from richLink
                            url = rich_link.get('richLinkProperties', {}).get('uri', '')
                            
                            # Extract display text (title) from richLink
                            title = rich_link.get('richLinkProperties', {}).get('title', '')
                            
                            text_parts.append(f"{title} [{url}]")
                                
            elif 'table' in element:
                # Handle tables
                table = element['table']
                for row in table.get('tableRows', []):
                    row_text = []
                    for cell in row.get('tableCells', []):
                        cell_text = self._extract_text_from_doc_structure({'body': {'content': cell.get('content', [])}})
                        row_text.append(cell_text.strip())
                    text_parts.append(' | '.join(row_text) + '\n')
        
        return ''.join(text_parts).strip()

    def _extract_text_from_sheet_structure(self, sheet: dict, service, spreadsheet_id: str) -> str:
        """Extract text from Google Sheets API response structure"""
        sheets = sheet.get('sheets', [])
        all_text = []
        
        for sheet_info in sheets:
            sheet_title = sheet_info.get('properties', {}).get('title', 'Sheet1')
            
            try:
                # Get the values from this sheet
                result = service.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range=sheet_title
                ).execute()
                
                values = result.get('values', [])
                if values:
                    all_text.append(f"=== {sheet_title} ===")
                    for row in values:
                        all_text.append(' | '.join(str(cell) for cell in row))
                    all_text.append("")
                    
            except Exception as e:
                print(f"Warning: Could not read sheet '{sheet_title}': {e}")
        
        return '\n'.join(all_text).strip()

    @staticmethod
    def _extract_document_id_and_type(url: str) -> Optional[tuple]:
        """
        Extract the document ID and type ('document' or 'spreadsheets') from common Google Docs/Sheets URL formats.
        """
        # Docs: https://docs.google.com/document/d/<DOC_ID>/...
        doc_pattern = r"docs\.google\.com/document/d/([a-zA-Z0-9_-]+)"
        # Sheets: https://docs.google.com/spreadsheets/d/<SHEET_ID>/...
        sheet_pattern = r"docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)"

        doc_match = re.search(doc_pattern, url)
        if doc_match:
            print(doc_match.group(1))
            return doc_match.group(1), "document"

        sheet_match = re.search(sheet_pattern, url)
        if sheet_match:
            print(sheet_match.group(1))
            return sheet_match.group(1), "spreadsheets"

        print("No match found")
        return None, None
