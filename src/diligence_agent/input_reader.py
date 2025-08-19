#!/usr/bin/env python3
"""
Input Sources Reader for Diligence Agent
Reads and validates JSON files containing input sources for company analysis.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class InputSource(BaseModel):
    """Schema for a single input source"""
    source: str = Field(..., description="Type of source (e.g., Google Docs, Slack, Webpage)")
    identifier: str = Field(..., description="URL, channel, or other identifier for the source")
    description: str = Field(..., description="Description of what information this source contains")
    
    @field_validator('source')
    @classmethod
    def validate_source(cls, v):
        """Validate source type"""
        valid_sources = ['Google Docs', 'Slack', 'Webpage', 'PDF', 'Email', 'Database', 'API']
        if v not in valid_sources:
            raise ValueError(f"Invalid source type: {v}. Must be one of {valid_sources}")
        return v
    
    @field_validator('identifier')
    @classmethod
    def validate_identifier(cls, v):
        """Basic validation for identifier"""
        if not v or not v.strip():
            raise ValueError("Identifier cannot be empty")
        return v.strip()


class InputSourcesData(BaseModel):
    """Schema for the complete input sources file"""
    company_name: str = Field(..., description="Name of the company being analyzed")
    company_sources: List[InputSource] = Field(..., description="List of input sources about the company")
    reference_sources: List[InputSource] = Field(..., description="List of reference sources to support the report creation")
    
    @field_validator('company_sources', 'reference_sources')
    @classmethod
    def validate_sources_not_empty(cls, v):
        """Ensure at least one input source is provided"""
        if not v:
            raise ValueError("At least one input source must be provided")
        return v


class InputReader:
    """Reader class for input sources JSON files"""
    
    def __init__(self, input_sources_dir: str = "input_sources"):
        """
        Initialize the reader with the input sources directory
        
        Args:
            input_sources_dir: Path to the directory containing JSON files
        """
        self.input_sources_dir = Path(input_sources_dir)
        if not self.input_sources_dir.exists():
            raise FileNotFoundError(f"Input sources directory not found: {input_sources_dir}")
    
    def read_company_sources(self, company_file: str) -> InputSourcesData:
        """
        Read and validate a company's input sources file
        
        Args:
            company_file: Name of the JSON file (e.g., 'baseten.json')
            
        Returns:
            Validated InputSourcesData object
        """
        file_path = self.input_sources_dir / company_file
        
        if not file_path.exists():
            raise FileNotFoundError(f"Company file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate against schema
            return InputSourcesData(**data)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {company_file}: {e}")
        except Exception as e:
            raise ValueError(f"Error reading {company_file}: {e}")
    
    def to_text(self, company_file: str) -> str:
        """
        Convert input sources to a formatted text representation
        
        Args:
            company_file: Name of the JSON file
            
        Returns:
            Formatted text string with all input sources
        """
        data = self.read_company_sources(company_file)
        
        text_lines = [
            f"Company: {data.company_name}",
            f"Number of Input Sources: {len(data.company_sources)}",
            "",
            "Input Sources:",
            "=" * 50
        ]
        
        for i, source in enumerate(data.input_sources, 1):
            text_lines.extend([
                f"{i}. Source: {source.source}",
                f"   Identifier: {source.identifier}",
                f"   Description: {source.description}",
                ""
            ])
        
        return "\n".join(text_lines)
    
    def to_dict(self, company_file: str) -> Dict[str, Any]:
        """
        Get the raw dictionary representation
        
        Args:
            company_file: Name of the JSON file
            
        Returns:
            Dictionary with input sources data
        """
        data = self.read_company_sources(company_file)
        return data.model_dump()
    
    def list_available_companies(self) -> List[str]:
        """
        List all available company input sources files
        
        Returns:
            List of company file names
        """
        json_files = list(self.input_sources_dir.glob("*.json"))
        return [f.name for f in json_files]
    
    def get_sources_by_type(self, company_file: str, source_type: str) -> List[InputSource]:
        """
        Get all sources of a specific type for a company
        
        Args:
            company_file: Name of the JSON file
            source_type: Type of source to filter by
            
        Returns:
            List of InputSource objects of the specified type
        """
        data = self.read_company_sources(company_file)
        return [source for source in data.input_sources if source.source == source_type]



