#!/usr/bin/env python3
"""Tests for the input_reader module."""

import sys
import os
import json
import tempfile
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from diligence_agent.input_reader import InputReader, InputSource, InputSourcesData


class TestInputSource:
    """Test suite for InputSource model."""
    
    def test_valid_input_source(self):
        """Test creating a valid input source."""
        source = InputSource(
            source="Google Docs",
            identifier="https://docs.google.com/document/d/123/edit",
            description="Test document"
        )
        assert source.source == "Google Docs"
        assert source.identifier == "https://docs.google.com/document/d/123/edit"
        assert source.description == "Test document"
    
    def test_invalid_source_type(self):
        """Test invalid source type raises error."""
        with pytest.raises(ValueError, match="Invalid source type"):
            InputSource(
                source="Invalid Source",
                identifier="https://example.com",
                description="Test"
            )
    
    def test_empty_identifier(self):
        """Test empty identifier raises error."""
        with pytest.raises(ValueError, match="Identifier cannot be empty"):
            InputSource(
                source="Google Docs",
                identifier="",
                description="Test"
            )


class TestInputSourcesData:
    """Test suite for InputSourcesData model."""
    
    def test_valid_input_sources_data(self):
        """Test creating valid input sources data."""
        data = InputSourcesData(
            company_name="TestCorp",
            company_sources=[
                InputSource(
                    source="Google Docs",
                    identifier="https://docs.google.com/document/d/123/edit",
                    description="Company doc"
                )
            ],
            reference_sources=[
                InputSource(
                    source="Webpage",
                    identifier="https://example.com",
                    description="Reference"
                )
            ]
        )
        assert data.company_name == "TestCorp"
        assert len(data.company_sources) == 1
        assert len(data.reference_sources) == 1
    
    def test_empty_company_sources(self):
        """Test empty company sources raises error."""
        with pytest.raises(ValueError, match="At least one input source must be provided"):
            InputSourcesData(
                company_name="TestCorp",
                company_sources=[],
                reference_sources=[
                    InputSource(
                        source="Webpage",
                        identifier="https://example.com",
                        description="Reference"
                    )
                ]
            )


class TestInputReader:
    """Test suite for InputReader class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sample_data = {
            "company_name": "TestCorp",
            "company_sources": [
                {
                    "source": "Google Docs",
                    "identifier": "https://docs.google.com/document/d/123/edit",
                    "description": "Test document"
                }
            ],
            "reference_sources": [
                {
                    "source": "Webpage",
                    "identifier": "https://example.com",
                    "description": "Reference"
                }
            ]
        }
    
    def test_reader_initialization(self):
        """Test reader initialization with valid directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            reader = InputReader(temp_dir)
            assert reader.input_sources_dir == Path(temp_dir)
    
    def test_reader_initialization_missing_dir(self):
        """Test reader initialization with missing directory."""
        with pytest.raises(FileNotFoundError):
            InputReader("/nonexistent/directory")
    
    def test_read_company_sources(self):
        """Test reading company sources from file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            test_file = Path(temp_dir) / "testcorp.json"
            with open(test_file, 'w') as f:
                json.dump(self.sample_data, f)
            
            # Read file
            reader = InputReader(temp_dir)
            data = reader.read_company_sources("testcorp.json")
            
            assert isinstance(data, InputSourcesData)
            assert data.company_name == "TestCorp"
            assert len(data.company_sources) == 1
            assert len(data.reference_sources) == 1
    
    def test_read_company_sources_file_not_found(self):
        """Test reading non-existent file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            reader = InputReader(temp_dir)
            with pytest.raises(FileNotFoundError):
                reader.read_company_sources("nonexistent.json")
    
    def test_read_company_sources_invalid_json(self):
        """Test reading invalid JSON file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "invalid.json"
            with open(test_file, 'w') as f:
                f.write("invalid json content")
            
            reader = InputReader(temp_dir)
            with pytest.raises(ValueError, match="Invalid JSON"):
                reader.read_company_sources("invalid.json")
    
    def test_list_available_companies(self):
        """Test listing available companies."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            Path(temp_dir, "company1.json").write_text(json.dumps(self.sample_data))
            Path(temp_dir, "company2.json").write_text(json.dumps({
                **self.sample_data,
                "company_name": "Company2"
            }))
            Path(temp_dir, "not_json.txt").write_text("some text")
            
            reader = InputReader(temp_dir)
            companies = reader.list_available_companies()
            
            assert len(companies) == 2
            assert "company1.json" in companies
            assert "company2.json" in companies
            assert "not_json.txt" not in companies
    
    def test_to_dict(self):
        """Test converting sources to dictionary."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "testcorp.json"
            with open(test_file, 'w') as f:
                json.dump(self.sample_data, f)
            
            reader = InputReader(temp_dir)
            data_dict = reader.to_dict("testcorp.json")
            
            assert data_dict["company_name"] == "TestCorp"
            assert len(data_dict["company_sources"]) == 1
            assert len(data_dict["reference_sources"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])