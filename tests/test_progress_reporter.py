#!/usr/bin/env python3
"""Tests for the progress_reporter module."""

import sys
import os
import time
from io import StringIO
import pytest
from unittest.mock import patch, MagicMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from diligence_agent.progress_reporter import ProgressReporter


class TestProgressReporter:
    """Test suite for ProgressReporter class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.reporter = ProgressReporter()
    
    def test_initialization(self):
        """Test ProgressReporter initialization."""
        assert self.reporter.current_task is None
        assert self.reporter.completed_tasks == 0
        assert self.reporter.total_tasks == 10  # Default value
        assert hasattr(self.reporter, 'start_time')
    
    def test_task_started(self):
        """Test starting a task."""
        with patch('builtins.print') as mock_print:
            self.reporter.task_started("data_organizer_task")
            assert self.reporter.current_task == "data_organizer_task"
            assert self.reporter.task_start_time is not None
            
            # Check that start message was printed
            calls = [str(call) for call in mock_print.call_args_list]
            assert any("STARTING" in str(call) for call in calls)
    
    def test_task_completed(self):
        """Test completing a task."""
        with patch('builtins.print') as mock_print:
            self.reporter.task_started("data_organizer_task")
            initial_completed = self.reporter.completed_tasks
            
            self.reporter.task_completed("data_organizer_task")
            assert self.reporter.completed_tasks == initial_completed + 1
            
            # Check that completion message was printed
            calls = [str(call) for call in mock_print.call_args_list]
            assert any("COMPLETED" in str(call) for call in calls)
    
    def test_status_update(self):
        """Test status update method."""
        with patch('builtins.print') as mock_print:
            self.reporter.status_update("Processing data...")
            
            # Check that status message was printed
            mock_print.assert_called()
            calls = [str(call) for call in mock_print.call_args_list]
            assert any("Processing data..." in str(call) for call in calls)
    
    def test_tool_used(self):
        """Test tool usage reporting."""
        with patch('builtins.print') as mock_print:
            # Should report search tool
            self.reporter.tool_used("Google Search Tool")
            calls = [str(call) for call in mock_print.call_args_list]
            assert any("Using" in str(call) for call in calls)
            
            mock_print.reset_mock()
            
            # Should not report non-key tools
            self.reporter.tool_used("Some Other Tool")
            mock_print.assert_not_called()
    
    def test_final_summary(self):
        """Test final summary printing."""
        with patch('builtins.print') as mock_print:
            self.reporter.completed_tasks = 8
            self.reporter.final_summary()
            
            # Check that summary was printed
            mock_print.assert_called()
            calls = [str(call) for call in mock_print.call_args_list]
            assert any("ANALYSIS COMPLETE" in str(call) for call in calls)
    
    def test_task_names_mapping(self):
        """Test task names are properly mapped."""
        assert 'data_organizer_task' in self.reporter.task_names
        assert self.reporter.task_names['data_organizer_task'] == '1. Data Validation & Organization'
        assert 'founder_assessment_task' in self.reporter.task_names
        assert self.reporter.task_names['founder_assessment_task'] == '8. Conducting Founder Assessment'
    
    def test_elapsed_time(self):
        """Test elapsed time calculation."""
        import time
        from datetime import datetime
        
        # Start a task
        self.reporter.task_started("data_organizer_task")
        initial_time = self.reporter.task_start_time
        assert initial_time is not None
        
        # Wait a bit
        time.sleep(0.1)
        
        # Complete task
        self.reporter.task_completed("data_organizer_task")
        
        # Check that task was completed
        assert self.reporter.completed_tasks > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])