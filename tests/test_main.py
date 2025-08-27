#!/usr/bin/env python3
"""Tests for the main module."""

import sys
import os
import json
import tempfile
from pathlib import Path
from datetime import datetime
import pytest
from unittest.mock import patch, MagicMock, call

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from diligence_agent.main import (
    organize_task_outputs,
    save_task_outputs,
    get_user_selection
)


class TestMainModule:
    """Test suite for main module functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sample_company_data = {
            "company_name": "TestCorp",
            "company_sources": [
                {
                    "source": "Google Docs",
                    "identifier": "https://docs.google.com/document/d/test123/edit",
                    "description": "Test document"
                }
            ],
            "reference_sources": [
                {
                    "source": "Webpage", 
                    "identifier": "https://example.com",
                    "description": "Reference"
                }
            ],
            "current_date": "2025-01-27"
        }
    
    def test_organize_task_outputs(self):
        """Test organizing task output files."""
        import os
        original_dir = os.getcwd()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Change to temp directory
                os.chdir(temp_dir)
                
                output_path = Path(temp_dir) / "output"
                output_path.mkdir()
                
                # Create task_outputs directory in current working directory
                task_outputs = Path("task_outputs")
                task_outputs.mkdir()
                (task_outputs / "1_data_validation.json").write_text('{"test": "data"}')
                (task_outputs / "2_overview.md").write_text("# Overview")
                (task_outputs / "3_product.md").write_text("# Product")
                
                # Organize outputs
                organize_task_outputs(output_path, "testcorp.json")
                
                # Check files were moved and renamed with company prefix
                assert (output_path / "task_outputs" / "testcorp_1_data_validation.json").exists()
                assert (output_path / "task_outputs" / "testcorp_2_overview.md").exists()
                assert (output_path / "task_outputs" / "testcorp_3_product.md").exists()
                
                # Check original files were moved (no longer in source)
                assert not (task_outputs / "1_data_validation.json").exists()
                assert not (task_outputs / "2_overview.md").exists()
                assert not (task_outputs / "3_product.md").exists()
            finally:
                # Restore original directory
                os.chdir(original_dir)
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_get_user_selection_single(self, mock_print, mock_input):
        """Test single company selection."""
        mock_input.return_value = "1"
        available = ["company1.json", "company2.json"]
        
        selected = get_user_selection(available)
        
        assert selected == ["company1.json"]
        mock_print.assert_called()
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_get_user_selection_multiple(self, mock_print, mock_input):
        """Test multiple company selection."""
        mock_input.return_value = "1,2"
        available = ["company1.json", "company2.json", "company3.json"]
        
        selected = get_user_selection(available)
        
        assert len(selected) == 2
        assert "company1.json" in selected
        assert "company2.json" in selected
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_get_user_selection_all(self, mock_print, mock_input):
        """Test selecting all companies."""
        # For 2 companies, "3" is the "All companies" option
        mock_input.return_value = "3"
        available = ["company1.json", "company2.json"]
        
        selected = get_user_selection(available)
        
        assert selected == available
    
    @patch('builtins.input')
    def test_get_user_selection_quit(self, mock_input):
        """Test quitting selection."""
        # For 1 company, "3" is the "Exit" option
        mock_input.return_value = "3"
        available = ["company1.json"]
        
        with pytest.raises(SystemExit):
            get_user_selection(available)
    
    def test_save_task_outputs(self):
        """Test saving task outputs from crew."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir)
            
            # Create mock crew with tasks
            mock_crew = MagicMock()
            mock_task1 = MagicMock()
            mock_task1.output = "# Test Overview"
            mock_task1.config = {"description": "overview section"}
            
            mock_task2 = MagicMock()
            mock_task2.output = '{"validated": true}'
            mock_task2.config = {"description": "data validation"}
            
            mock_crew.tasks = [mock_task1, mock_task2]
            
            # Save outputs
            save_task_outputs(mock_crew, output_path, "testcorp.json")
            
            # Check that task_outputs directory was created
            assert (output_path / "task_outputs").exists()
            
            # Check that at least the summary file was created
            summary_files = list((output_path / "task_outputs").glob("*task_summary.md"))
            assert len(summary_files) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])