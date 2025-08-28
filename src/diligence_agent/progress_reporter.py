"""
Progress Reporter for Diligence Agent

Provides real-time status updates during crew execution.
"""

from datetime import datetime
from typing import Dict, Any, Optional
import sys


class ProgressReporter:
    """Reports progress of crew execution with timestamps and task counts."""
    
    def __init__(self, total_tasks: int = 10):
        self.total_tasks = total_tasks
        self.completed_tasks = 0
        self.current_task = None
        self.start_time = datetime.now()
        self.task_start_time = None
        self.task_names = {
            'data_organizer_task': '1. Data Validation & Organization',
            'overview_section_writer_task': '2. Writing Overview Section',
            'why_interesting_section_writer_task': '3. Writing Why Interesting Section',
            'product_section_writer_task': '4. Writing Product Section',
            'market_section_writer_task': '5. Writing Market Section',
            'competitive_landscape_section_writer_task': '6. Writing Competitive Landscape',
            'team_section_writer_task': '7. Writing Team Section',
            'founder_assessment_task': '8. Conducting Founder Assessment',
            'report_writer_task': '9. Compiling Full Report',
            'executive_summary_task': '10. Creating Executive Summary & Recommendation'
        }
    
    def task_started(self, task_name: str, agent_name: Optional[str] = None):
        """Report when a task starts."""
        self.task_start_time = datetime.now()
        self.current_task = task_name
        
        # Calculate elapsed time
        elapsed = (datetime.now() - self.start_time).total_seconds()
        elapsed_min = int(elapsed // 60)
        elapsed_sec = int(elapsed % 60)
        
        # Get friendly task name
        friendly_name = self.task_names.get(task_name, task_name)
        
        # Clear line and print status
        print(f"\n{'='*70}")
        print(f"⏱️  Elapsed: {elapsed_min:02d}:{elapsed_sec:02d} | Progress: {self.completed_tasks}/{self.total_tasks} tasks completed")
        print(f"🚀 STARTING: {friendly_name}")
        if agent_name:
            print(f"   Agent: {agent_name}")
        print(f"{'='*70}")
        sys.stdout.flush()
    
    def task_completed(self, task_name: str):
        """Report when a task completes."""
        self.completed_tasks += 1
        
        # Calculate task duration
        if self.task_start_time:
            task_duration = (datetime.now() - self.task_start_time).total_seconds()
            duration_min = int(task_duration // 60)
            duration_sec = int(task_duration % 60)
            duration_str = f"{duration_min:02d}:{duration_sec:02d}"
        else:
            duration_str = "N/A"
        
        # Get friendly task name
        friendly_name = self.task_names.get(task_name, task_name)
        
        print(f"\n✅ COMPLETED: {friendly_name}")
        print(f"   Duration: {duration_str}")
        print(f"   Progress: {self.completed_tasks}/{self.total_tasks} tasks done")
        
        # Estimate remaining time
        if self.completed_tasks > 0:
            elapsed_total = (datetime.now() - self.start_time).total_seconds()
            avg_per_task = elapsed_total / self.completed_tasks
            remaining_tasks = self.total_tasks - self.completed_tasks
            estimated_remaining = remaining_tasks * avg_per_task
            est_min = int(estimated_remaining // 60)
            est_sec = int(estimated_remaining % 60)
            print(f"   Estimated time remaining: ~{est_min:02d}:{est_sec:02d}")
        
        sys.stdout.flush()
    
    def status_update(self, message: str):
        """Print a status update."""
        print(f"   📍 {message}")
        sys.stdout.flush()
    
    def tool_used(self, tool_name: str):
        """Report when a tool is used."""
        # Only report key tools to avoid clutter
        if any(keyword in tool_name.lower() for keyword in ['search', 'google', 'scrape']):
            print(f"   🔧 Using: {tool_name}")
            sys.stdout.flush()
    
    def final_summary(self):
        """Print final execution summary."""
        total_time = (datetime.now() - self.start_time).total_seconds()
        total_min = int(total_time // 60)
        total_sec = int(total_time % 60)
        
        print(f"\n{'='*70}")
        print(f"🎉 ANALYSIS COMPLETE!")
        print(f"   Total time: {total_min:02d}:{total_sec:02d}")
        print(f"   Tasks completed: {self.completed_tasks}/{self.total_tasks}")
        print(f"{'='*70}\n")
        sys.stdout.flush()


# Global progress reporter instance
_progress_reporter = None

def get_progress_reporter() -> ProgressReporter:
    """Get or create the global progress reporter."""
    global _progress_reporter
    if _progress_reporter is None:
        _progress_reporter = ProgressReporter()
    return _progress_reporter

def reset_progress_reporter():
    """Reset the progress reporter for a new run."""
    global _progress_reporter
    _progress_reporter = ProgressReporter()
    return _progress_reporter