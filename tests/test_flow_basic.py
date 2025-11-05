#!/usr/bin/env python3
"""Basic tests for the flow module."""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from diligence_agent.flow import DiligenceFlow, DiligenceState
from diligence_agent.schemas import DataSources, ReportStructure


class TestFlowBasic:
    """Basic test suite for flow module."""
    
    def test_diligence_state_initialization(self):
        """Test DiligenceState initialization with defaults."""
        state = DiligenceState()
        
        assert state.company_name == ""
        assert state.current_date == ""
        assert state.batch_size == 1
        assert state.batch_delay == 0.0
        assert hasattr(state, 'num_search_terms')
        assert hasattr(state, 'num_websites')
        # Check data sources type and fields
        assert hasattr(state.data_sources, 'google_docs')
        assert hasattr(state.data_sources, 'websites')
        assert hasattr(state.data_sources, 'pdfs')
        assert hasattr(state.data_sources, 'slack_channels')
        
        # Check report structure type and fields
        assert hasattr(state.report_structure, 'company_overview_section')
        assert hasattr(state.report_structure, 'product_section')
        assert state.final_report == ""
        
        # Check default sections
        expected_sections = [
            "Get Data Sources",
            "Parse Data Sources", 
            "Company Overview",            
            "Product",
            "Competitive Landscape",
            "Market", 
            "Founders",
            "Why Interesting",
            "Report Conclusion",
            "Final Report"
        ]
        assert state.sections_to_run == expected_sections
    
    def test_diligence_flow_initialization(self):
        """Test DiligenceFlow can be initialized."""
        flow = DiligenceFlow()
        assert isinstance(flow, DiligenceFlow)
        assert hasattr(flow, 'state')
    
    def test_data_sources_schema(self):
        """Test DataSources schema creation."""
        data_sources = DataSources(
            google_docs=["https://docs.google.com/document/d/test123/edit"],
            websites=["https://example.com"],
            pdfs=["test.pdf"],
            slack_channels=["channel123"]
        )
        
        assert len(data_sources.google_docs) == 1
        assert len(data_sources.websites) == 1
        assert len(data_sources.pdfs) == 1
        assert len(data_sources.slack_channels) == 1
        assert "test123" in data_sources.google_docs[0]
    
    def test_report_structure_schema(self):
        """Test ReportStructure schema creation."""
        report = ReportStructure(
            company_overview_section="Test overview",
            product_section="Test product",
            why_interesting_section="Test interesting",
            founders_section="Test founders",
            competitive_landscape_section="Test competitive",
            market_section="Test market",
            report_conclusion_section="Test conclusion"
        )
        
        assert report.company_overview_section == "Test overview"
        assert report.product_section == "Test product"
        assert report.why_interesting_section == "Test interesting"
        assert report.founders_section == "Test founders"
        assert report.competitive_landscape_section == "Test competitive"
        assert report.market_section == "Test market"
        assert report.report_conclusion_section == "Test conclusion"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])