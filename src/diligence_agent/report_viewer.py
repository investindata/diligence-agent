import gradio as gr
from pathlib import Path
from typing import Dict, Optional, List
import os
import base64
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
        """Get only companies that have any reports"""
        all_companies = self.get_available_companies()
        companies_with_reports = []
        
        for company in all_companies:
            if self.get_available_reports(company):
                companies_with_reports.append(company)
        
        return companies_with_reports
    
    def get_available_reports(self, company_name: str) -> List[Dict[str, str]]:
        """Get all available reports for a company"""
        if not company_name:
            return []
            
        output_dir = Path("output")
        if not output_dir.exists():
            return []
        
        # Scan all session directories
        session_dirs = list(output_dir.glob("session_*"))
        if not session_dirs:
            return []
        
        reports = []
        report_patterns = {
            "Executive Summary": f"{company_name}_executive_summary.md",
            "Full Report": f"{company_name}_full_due_diligence_report.md"
        }
        
        # Look for known report types
        for report_type, filename in report_patterns.items():
            latest_file = self.find_latest_report_by_filename(filename, session_dirs)
            if latest_file:
                reports.append({
                    "type": report_type,
                    "path": str(latest_file),
                    "filename": filename
                })
        
        # Look for other potential reports (future extensibility)
        for session_dir in session_dirs:
            for file_path in session_dir.glob(f"{company_name}_*.md"):
                filename = file_path.name
                # Skip already processed files
                if filename not in [r["filename"] for r in reports]:
                    # Create a readable name from filename
                    report_type = filename.replace(f"{company_name}_", "").replace(".md", "").replace("_", " ").title()
                    latest_file = self.find_latest_report_by_filename(filename, session_dirs)
                    if latest_file:
                        reports.append({
                            "type": report_type,
                            "path": str(latest_file),
                            "filename": filename
                        })
        
        return reports
    
    def find_latest_report_by_filename(self, filename: str, session_dirs: List[Path]) -> Optional[Path]:
        """Find the latest version of a specific report file across sessions"""
        matching_files = []
        
        for session_dir in session_dirs:
            file_path = session_dir / filename
            if file_path.exists():
                matching_files.append(file_path)
        
        if not matching_files:
            return None
        
        # Return the most recently modified file
        return max(matching_files, key=lambda p: p.stat().st_mtime)
    
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
    
    def load_report_content(self, company_name: str, report_type: str) -> str:
        """Load and return report content for the selected company and report type"""
        if not company_name or not report_type:
            return ""
        
        available_reports = self.get_available_reports(company_name)
        selected_report = None
        
        for report in available_reports:
            if report["type"] == report_type:
                selected_report = report
                break
        
        if not selected_report:
            return f"No **{report_type}** found for **{company_name}**."
        
        try:
            report_path = Path(selected_report["path"])
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Add metadata header
            mod_time = datetime.fromtimestamp(report_path.stat().st_mtime)
            session_name = report_path.parent.name
            
            metadata_header = f"""---
**Company:** {company_name}  
**Report Type:** {report_type}  
**Report File:** `{report_path.name}`  
**Session:** {session_name}  
**Last Updated:** {mod_time.strftime('%Y-%m-%d %H:%M:%S')}  
---

"""
            
            return metadata_header + content
            
        except Exception as e:
            return f"Error loading **{report_type}** for **{company_name}**: {str(e)}"
    
    def get_report_types_for_company(self, company_name: str) -> List[str]:
        """Get available report types for a company"""
        if not company_name:
            return []
        
        available_reports = self.get_available_reports(company_name)
        return [report["type"] for report in available_reports]
    
    def create_interface(self):
        """Create the Gradio interface for report viewing"""
        
        with gr.Blocks(
            title="InvestInData Due Diligence Reports", 
            theme='JohnSmith9982/small_and_pretty'
        ) as demo:
            # Get logo and embed inline with base64
            logo_path = Path(__file__).parent / "assets" / "iid_logo.webp"
            
            if logo_path.exists():
                try:
                    # Read and encode logo as base64
                    with open(logo_path, "rb") as img_file:
                        img_data = base64.b64encode(img_file.read()).decode()
                    
                    title_html = f'''
                    <h1 style="display: flex; align-items: center; margin: 0;">
                        <img src="data:image/webp;base64,{img_data}" 
                             style="height: 60px !important; width: auto !important; margin-right: 12px; max-height: 60px;">
                        InvestInData - Due Diligence Reports
                    </h1>
                    '''
                    gr.HTML(title_html)
                except Exception as e:
                    gr.Markdown("# 📊 InvestInData - Due Diligence Reports")
            else:
                gr.Markdown("# 📊 InvestInData - Due Diligence Reports")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Selection")
                    
                    companies_with_reports = self.get_companies_with_reports()
                    company_dropdown = gr.Dropdown(
                        label="Select Company",
                        choices=companies_with_reports,
                        value=None,  # Start with no selection
                        interactive=True
                    )
                    
                    report_type_dropdown = gr.Dropdown(
                        label="Select Report",
                        choices=[],
                        value=None,  # Start with no selection
                        interactive=True
                    )
                
                with gr.Column(scale=3):
                    gr.Markdown("### Report")
                    
                    report_display = gr.Markdown(
                        value="",  # Start blank
                        height=600,
                        show_copy_button=True,
                        container=True
                    )
            
            # Event handlers
            def update_report_types(company_name):
                """Update report type dropdown when company changes"""
                if not company_name:
                    return gr.update(choices=[], value=None)
                
                report_types = self.get_report_types_for_company(company_name)
                return gr.update(choices=report_types, value=None)
            
            def update_report_content(company_name, report_type):
                """Update report content when company or report type changes"""
                return self.load_report_content(company_name, report_type)
            
            # Company selection updates report types
            company_dropdown.change(
                fn=update_report_types,
                inputs=[company_dropdown],
                outputs=[report_type_dropdown]
            )
            
            # Both company and report type selection update content
            for component in [company_dropdown, report_type_dropdown]:
                component.change(
                    fn=update_report_content,
                    inputs=[company_dropdown, report_type_dropdown],
                    outputs=[report_display]
                )
            
            # Load initial state (blank)
            demo.load(
                fn=lambda: "",
                inputs=[],
                outputs=[report_display]
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