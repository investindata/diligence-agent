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
        document_id = self._extract_document_id(google_doc_url)
        if document_id is None:
            raise ValueError("Could not extract Google Doc ID from the provided URL.")

        # Try plain text export first (works for public or 'anyone with link' docs)
        export_urls = [
            f"https://docs.google.com/document/d/{document_id}/export?format=txt",
            f"https://docs.google.com/document/d/{document_id}/export?format=html",
        ]

        last_error: Optional[str] = None
        for export_url in export_urls:
            try:
                response = requests.get(export_url, timeout=30)
                if response.status_code == 200:
                    text = response.text
                    # If HTML, do a very light tag strip fallback
                    if "<html" in text.lower():
                        text = re.sub(r"<[^>]+>", "\n", text)
                        text = re.sub(r"\n{2,}", "\n\n", text).strip()
                    return text.strip()
                else:
                    last_error = f"HTTP {response.status_code} for {export_url}"
            except Exception as exc:  # noqa: BLE001 - surfacing any network error is fine here
                last_error = str(exc)

        raise RuntimeError(
            "Failed to fetch Google Doc content. Ensure the document is shared as 'Anyone with the link' "
            "or set up authenticated access. Last error: " + (last_error or "unknown")
        )

    @staticmethod
    def _extract_document_id(url: str) -> Optional[str]:
        """Extract the document ID from common Google Docs URL formats."""
        # Examples:
        # https://docs.google.com/document/d/<DOC_ID>/edit
        # https://docs.google.com/document/d/<DOC_ID>/view?usp=sharing
        # https://docs.google.com/document/d/<DOC_ID>/
        pattern = r"docs\.google\.com/document/d/([a-zA-Z0-9_-]+)"
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        return None
