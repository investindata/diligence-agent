#!/usr/bin/env python3
"""
Tests for Input Sources Reader
"""
import sys
import os
import pytest
import tempfile
import json
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from diligence_agent.input_reader import InputReader, InputSource, InputSourcesData


class TestInputReader:
    """Test cases for InputReader"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.test_data = {
            "company_name": "Test Company",
            "input_sources": [
                {
                    "source": "Google Docs",
                    "identifier": "https://docs.google.com/document/d/test123/edit",
                    "description": "Test due diligence document"
                },
                {
                    "source": "Webpage",
                    "identifier": "https://testcompany.com",
                    "description": "Company website"
                }
            ]
        }
    
    def test_input_source_validation(self):
        """Test InputSource validation"""
        # Valid source
        valid_source = InputSource(
            source="Google Docs",
            identifier="https://example.com",
            description="Test description"
        )
        assert valid_source.source == "Google Docs"
        
        # Invalid source type
        with pytest.raises(ValueError, match="Invalid source type"):
            InputSource(
                source="Invalid Source",
                identifier="https://example.com",
                description="Test description"
            )
        
        # Empty identifier
        with pytest.raises(ValueError, match="Identifier cannot be empty"):
            InputSource(
                source="Google Docs",
                identifier="",
                description="Test description"
            )
    
    def test_input_sources_data_validation(self):
        """Test InputSourcesData validation"""
        # Valid data
        valid_data = InputSourcesData(**self.test_data)
        assert valid_data.company_name == "Test Company"
        assert len(valid_data.input_sources) == 2
        
        # Empty input sources
        invalid_data = self.test_data.copy()
        invalid_data["input_sources"] = []
        with pytest.raises(ValueError, match="At least one input source must be provided"):
            InputSourcesData(**invalid_data)
    
    def test_reader_with_temp_files(self):
        """Test reader with temporary files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test JSON file
            test_file = Path(temp_dir) / "test_company.json"
            with open(test_file, 'w') as f:
                json.dump(self.test_data, f)
            
            # Test reader
            reader = InputReader(temp_dir)
            
            # Test reading
            data = reader.read_company_sources("test_company.json")
            assert data.company_name == "Test Company"
            
            # Test to_text
            text = reader.to_text("test_company.json")
            assert "Test Company" in text
            assert "Google Docs" in text
            
            # Test to_dict
            data_dict = reader.to_dict("test_company.json")
            assert data_dict["company_name"] == "Test Company"
            
            # Test list_available_companies
            companies = reader.list_available_companies()
            assert "test_company.json" in companies
            
            # Test get_sources_by_type
            google_docs = reader.get_sources_by_type("test_company.json", "Google Docs")
            assert len(google_docs) == 1
            assert google_docs[0].identifier == "https://docs.google.com/document/d/test123/edit"
    
    def test_reader_file_not_found(self):
        """Test reader with non-existent file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            reader = InputReader(temp_dir)
            
            with pytest.raises(FileNotFoundError):
                reader.read_company_sources("nonexistent.json")
    
    def test_reader_invalid_json(self):
        """Test reader with invalid JSON"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create invalid JSON file
            test_file = Path(temp_dir) / "invalid.json"
            with open(test_file, 'w') as f:
                f.write("invalid json content")
            
            reader = InputReader(temp_dir)
            
            with pytest.raises(ValueError, match="Invalid JSON"):
                reader.read_company_sources("invalid.json")
    
    def test_reader_directory_not_found(self):
        """Test reader with non-existent directory"""
        with pytest.raises(FileNotFoundError):
            InputReader("nonexistent_directory")


if __name__ == "__main__":
    # Run tests directly if script is executed
    pytest.main([__file__, "-v"])
