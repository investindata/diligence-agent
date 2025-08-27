import gradio as gr
from pathlib import Path
from typing import Dict, Optional, List
import os
from datetime import datetime

from diligence_agent.input_reader import InputReader


class ReportViewer:
    """Gradio UI for viewing completed investment reports"""
    
    def __init__(self):
        self.input_reader = InputReader()
        
    def get_available_companies(self) -> List[str]:
        """Get all companies from input_sources directory"""
        try:
            available = self.input_reader.list_available_companies()
            return [c.replace('.json', '') for c in available]
        except Exception as e:
            print(f"Error getting companies: {e}")
            return []
    
    def get_companies_with_reports(self) -> List[str]:
        """Get only companies that have executive summary reports"""
        all_companies = self.get_available_companies()
        companies_with_reports = []
        
        for company in all_companies:
            if self.find_latest_report(company):
                companies_with_reports.append(company)
        
        return companies_with_reports
    
    def find_latest_report(self, company_name: str) -> Optional[Path]:
        """Find the latest executive summary report for a company"""
        if not company_name:
            return None
            
        output_dir = Path("output")
        if not output_dir.exists():
            return None
        
        # Scan all session directories
        session_dirs = list(output_dir.glob("session_*"))
        if not session_dirs:
            return None
        
        # Look for executive summary files for this company
        report_files = []
        for session_dir in session_dirs:
            potential_files = [
                session_dir / f"{company_name}_executive_summary.md",
                session_dir / f"{company_name.lower()}_executive_summary.md",
                session_dir / f"{company_name.upper()}_executive_summary.md",
                session_dir / f"{company_name.title()}_executive_summary.md",
            ]
            
            for file_path in potential_files:
                if file_path.exists():
                    report_files.append(file_path)
                    break
        
        if not report_files:
            return None
        
        # Return the most recently modified file
        latest_report = max(report_files, key=lambda p: p.stat().st_mtime)
        return latest_report
    
    def load_report_content(self, company_name: str) -> str:
        """Load and return report content for the selected company"""
        if not company_name:
            return "Please select a company to view its report."
        
        report_path = self.find_latest_report(company_name)
        
        if not report_path:
            return f"No executive summary report found for **{company_name}**.\n\nPlease run an analysis for this company first."
        
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Add metadata header
            mod_time = datetime.fromtimestamp(report_path.stat().st_mtime)
            session_name = report_path.parent.name
            
            metadata_header = f"""---
**Company:** {company_name}  
**Report File:** `{report_path.name}`  
**Session:** {session_name}  
**Last Updated:** {mod_time.strftime('%Y-%m-%d %H:%M:%S')}  
---

"""
            
            return metadata_header + content
            
        except Exception as e:
            return f"Error loading report for **{company_name}**: {str(e)}"
    
    def get_report_info(self, company_name: str) -> str:
        """Get basic info about the report status"""
        if not company_name:
            return "No company selected"
        
        report_path = self.find_latest_report(company_name)
        
        if not report_path:
            return f"❌ No report available for {company_name}"
        
        mod_time = datetime.fromtimestamp(report_path.stat().st_mtime)
        session_name = report_path.parent.name
        
        return f"✅ Latest report: {session_name} ({mod_time.strftime('%Y-%m-%d %H:%M')})"
    
    def create_interface(self):
        """Create the Gradio interface for report viewing"""
        
        with gr.Blocks(
            title="Due Diligence Report Viewer", 
            theme='JohnSmith9982/small_and_pretty'
        ) as demo:
            gr.Markdown("# 📊 Due Diligence Report Viewer")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Company Selection")
                    
                    companies_with_reports = self.get_companies_with_reports()
                    company_dropdown = gr.Dropdown(
                        label="Select Company",
                        choices=companies_with_reports,
                        value=None,  # Start with no selection
                        interactive=True
                    )
                    
                    report_status = gr.Textbox(
                        label="Report Status",
                        value="No company selected",
                        interactive=False,
                        lines=2
                    )
                
                with gr.Column(scale=3):
                    gr.Markdown("### Executive Summary Report")
                    
                    report_display = gr.Markdown(
                        value="",  # Start blank
                        height=600,
                        show_copy_button=True,
                        container=True
                    )
            
            # Event handler for company selection
            company_dropdown.change(
                fn=lambda company: (
                    self.get_report_info(company),
                    self.load_report_content(company)
                ),
                inputs=[company_dropdown],
                outputs=[report_status, report_display]
            )
            
            # Load initial state (blank)
            demo.load(
                fn=lambda: (
                    "No company selected",
                    ""
                ),
                inputs=[],
                outputs=[report_status, report_display]
            )
        
        return demo


def launch_report_viewer():
    """Launch the report viewer UI"""
    viewer = ReportViewer()
    demo = viewer.create_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7861,  # Different port to avoid conflicts
        share=False,
        debug=True,
        inbrowser=True
    )


if __name__ == "__main__":
    launch_report_viewer()