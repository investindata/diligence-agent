from crewai.tools import BaseTool
from typing import Type, Optional
from pydantic import BaseModel, Field
import re
import requests


class GoogleDocProcessorInput(BaseModel):
    """Input schema for GoogleDocProcessor."""
    google_doc_url: str = Field(..., description="The URL of the Google Doc to process.")

class GoogleDocProcessor(BaseTool):
    name: str = "Google Doc Processor"
    description: str = (
        "Process a Google Doc and return the content as a string."
    )
    args_schema: Type[BaseModel] = GoogleDocProcessorInput

    def _run(self, google_doc_url: str) -> str:
        document_id, doc_type = self._extract_document_id_and_type(google_doc_url)
        if document_id is None or doc_type is None:
            raise ValueError("Could not extract Google Doc/Sheet ID and type from the provided URL.")

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
                    return text.strip()
                else:
                    last_error = f"HTTP {response.status_code} for {export_url}"
            except Exception as exc:
                last_error = str(exc)

        raise RuntimeError(
            "Failed to fetch Google Doc/Sheet content. Ensure the document is shared as 'Anyone with the link' "
            "or set up authenticated access. Last error: " + (last_error or "unknown")
        )

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
