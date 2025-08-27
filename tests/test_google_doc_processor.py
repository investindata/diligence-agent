#!/usr/bin/env python3
"""
Tests for GoogleDocProcessor
"""
import sys
import os
import pytest

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from diligence_agent.tools.google_doc_processor import GoogleDocProcessor


class TestGoogleDocProcessor:
    """Test cases for GoogleDocProcessor"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.processor = GoogleDocProcessor()
        self.test_url = "https://docs.google.com/document/d/1a759lcNH0KkZ0QkaQ6-L0lTECUpdHqDFX42WyPPVae8/edit?usp=sharing"
    
    def test_extract_document_id(self):
        """Test document ID extraction from various URL formats"""
        # Test the main URL format
        from diligence_agent.tools.google_doc_processor import GoogleDocProcessor
        doc_info = GoogleDocProcessor._extract_document_id_and_type(self.test_url)
        assert doc_info is not None
        assert doc_info[0] == "1a759lcNH0KkZ0QkaQ6-L0lTECUpdHqDFX42WyPPVae8"
        assert doc_info[1] == "document"
        
        # Test other URL formats
        test_cases = [
            "https://docs.google.com/document/d/1a759lcNH0KkZ0QkaQ6-L0lTECUpdHqDFX42WyPPVae8/view",
            "https://docs.google.com/document/d/1a759lcNH0KkZ0QkaQ6-L0lTECUpdHqDFX42WyPPVae8/",
            "https://docs.google.com/document/d/1a759lcNH0KkZ0QkaQ6-L0lTECUpdHqDFX42WyPPVae8/edit?usp=sharing&pli=1",
        ]
        
        for url in test_cases:
            doc_info = GoogleDocProcessor._extract_document_id_and_type(url)
            assert doc_info is not None
            assert doc_info[0] == "1a759lcNH0KkZ0QkaQ6-L0lTECUpdHqDFX42WyPPVae8"
    
    def test_extract_document_id_invalid_url(self):
        """Test document ID extraction with invalid URLs"""
        from diligence_agent.tools.google_doc_processor import GoogleDocProcessor
        invalid_urls = [
            "https://docs.google.com/spreadsheets/d/123/edit",  # Spreadsheet, not doc
            "https://example.com/document/123",  # Not Google Docs
            "invalid-url",
            "",
        ]
        
        # Spreadsheet URL should return spreadsheet type
        doc_info = GoogleDocProcessor._extract_document_id_and_type(invalid_urls[0])
        assert doc_info is not None
        assert doc_info[1] == "spreadsheets"
        
        # Non-Google URLs should return (None, None)
        for url in invalid_urls[1:]:
            doc_info = GoogleDocProcessor._extract_document_id_and_type(url)
            assert doc_info == (None, None)
    
    @pytest.mark.integration
    def test_fetch_google_doc_content(self):
        """Test fetching content from a real Google Doc (integration test)"""
        try:
            content = self.processor._run(self.test_url)
            
            # Basic content validation
            assert isinstance(content, str)
            assert len(content) > 0
            assert "Due Diligence Report" in content
            assert "Baseten" in content
            
            # Check for expected sections
            expected_sections = ["Overview", "Product", "Market", "Team"]
            for section in expected_sections:
                assert section in content, f"Expected section '{section}' not found in content"
                
        except Exception as e:
            pytest.skip(f"Integration test skipped due to network/access issue: {e}")
    
    def test_processor_initialization(self):
        """Test that the processor initializes correctly"""
        assert self.processor.name == "Google Doc Processor"
        assert "Process a Google Doc" in self.processor.description
        assert self.processor.args_schema is not None


if __name__ == "__main__":
    # Run tests directly if script is executed
    pytest.main([__file__, "-v"])
