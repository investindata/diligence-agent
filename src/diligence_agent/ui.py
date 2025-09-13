import gradio as gr
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import os
import base64
import threading
import subprocess
import sys
import json
import asyncio
from datetime import datetime

from diligence_agent.flow import kickoff


class DueDiligenceUI:
    """Gradio UI for running analysis and viewing investment reports"""
    
    def __init__(self):
        pass
        
    def get_available_companies(self) -> List[str]:
        """Get all companies that have existing reports from task_outputs directory"""
        try:
            task_outputs_dir = Path("task_outputs")
            if not task_outputs_dir.exists():
                return []
            
            companies = []
            for company_dir in task_outputs_dir.iterdir():
                if company_dir.is_dir():
                    companies.append(company_dir.name)
            
            return sorted(companies)
        except Exception as e:
            print(f"Error getting companies: {e}")
            return []
    
    def run_analysis(self, data_sources_url: str, num_search_terms: int = 5, num_websites: int = 10, model: str = "gpt-4.1-mini", progress_callback=None) -> str:
        """Run the diligence analysis using the flow system with data sources URL"""
        if not data_sources_url:
            return "No data sources URL provided"
        
        try:
            if progress_callback:
                progress_callback("Starting flow-based analysis...")
            
            # Run the analysis using the flow system directly
            async def run_flow():
                return await kickoff(
                    data_sources_file=data_sources_url,
                    num_search_terms=num_search_terms,
                    num_websites=num_websites,
                    model=model
                )
            
            # Create a new event loop for the async call
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            if progress_callback:
                progress_callback("Running flow analysis...")
            
            result = loop.run_until_complete(run_flow())
            
            if progress_callback:
                progress_callback("Flow analysis completed successfully!")
            
            return f"Analysis completed successfully! Flow ID: {getattr(result, 'id', 'unknown')}"
                
        except Exception as e:
            error_msg = f"Error running flow analysis: {str(e)}"
            if progress_callback:
                progress_callback(error_msg)
            return error_msg
    
    def get_companies_with_reports(self) -> List[str]:
        """Get only companies that have any reports"""
        all_companies = self.get_available_companies()
        companies_with_reports = []
        
        for company in all_companies:
            if self.get_available_reports(company):
                companies_with_reports.append(company)
        
        return companies_with_reports
    
    def get_available_reports(self, company_name: str) -> List[Dict[str, str]]:
        """Get all available reports for a company from task_outputs directory"""
        if not company_name:
            return []
            
        # Look in task_outputs directory (new flow-based structure)
        task_outputs_dir = Path("task_outputs") / company_name
        if not task_outputs_dir.exists():
            return []
        
        reports = []
        
        # Find all files that match the numbered pattern
        for file_path in task_outputs_dir.glob("[0-9]*"):
            filename = file_path.name
            
            # Extract report type from filename
            # Format: {number}.{description}.{ext}
            # e.g., "8.final_report.md" -> "Final Report"
            
            # Extract number and description
            number_prefix = ""
            if "." in filename:
                parts = filename.split(".", 2)  # Split into at most 3 parts: number, description, extension
                if len(parts) >= 2 and parts[0].isdigit():
                    number_prefix = parts[0] + ". "
                    name_parts = parts[1]
                else:
                    name_parts = filename.rsplit(".", 1)[0]  # Remove extension only
            else:
                name_parts = filename
            
            # Convert to readable format
            report_type = number_prefix + name_parts.replace("_", " ").title()
            
            reports.append({
                "type": report_type,
                "path": str(file_path),
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
            
            # Check if it's a JSON file
            if report_path.suffix.lower() == '.json':
                try:
                    # Parse and format JSON
                    json_data = json.loads(content)
                    formatted_json = json.dumps(json_data, indent=2)
                    
                    # Simple metadata for JSON
                    metadata = f"**{report_type}** - {datetime.fromtimestamp(report_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    return metadata + f"```json\n{formatted_json}\n```"
                except json.JSONDecodeError:
                    # Fall back to plain text if invalid JSON
                    pass
            
            # Default markdown formatting with full metadata
            mod_time = datetime.fromtimestamp(report_path.stat().st_mtime)
            
            metadata_header = f"""---
**Company:** {company_name}  
**Report Type:** {report_type}  
**Report File:** `{report_path.name}`  
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
        report_types = [report["type"] for report in available_reports]
        
        # Sort numerically by number prefix, then alphabetically
        def sort_key(report_type):
            if ". " in report_type:
                number_part = report_type.split(". ", 1)[0]
                try:
                    return (0, int(number_part))  # (sort_group, number)
                except ValueError:
                    return (1, report_type)  # Non-numeric prefixes come after
            else:
                return (1, report_type)  # No number prefix, sort alphabetically after numbered items
        
        return sorted(report_types, key=sort_key)
    
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
                    gr.Markdown("### Analysis")
                    
                    # Data Sources URL input
                    data_sources_input = gr.Textbox(
                        label="Data Sources URL",
                        placeholder="Paste Google Doc URL containing company data sources...",
                        lines=2,
                        interactive=True
                    )
                    
                    # Research parameters
                    gr.Markdown("**Research Parameters**")
                    
                    search_terms_slider = gr.Slider(
                        label="Search Terms",
                        minimum=1,
                        maximum=20,
                        value=5,
                        step=1,
                        info="Number of search terms to generate for research",
                        interactive=True
                    )
                    
                    websites_slider = gr.Slider(
                        label="Websites per Search",
                        minimum=1,
                        maximum=50,
                        value=10,
                        step=1,
                        info="Number of websites to scrape per search term",
                        interactive=True
                    )
                    
                    model_dropdown = gr.Dropdown(
                        label="Model",
                        choices=["gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1"],
                        value="gpt-4.1-mini",
                        info="LLM model to use for analysis",
                        interactive=True
                    )
                    
                    # Add Run Analysis button
                    run_analysis_btn = gr.Button(
                        "Run Analysis",
                        interactive=True,
                        variant="primary"
                    )
                    
                    gr.Markdown("### View Reports")
                    
                    # Show all companies for selection
                    all_companies = self.get_available_companies()
                    company_dropdown = gr.Dropdown(
                        label="Select Company",
                        choices=all_companies,
                        value=None,  # Start with no selection
                        interactive=True
                    )
                    
                    # Progress display
                    progress_display = gr.Textbox(
                        label="Progress",
                        value="",
                        interactive=False,
                        visible=False
                    )
                    
                    # Report type dropdown - only shown after reports are created
                    report_type_dropdown = gr.Dropdown(
                        label="Select Report",
                        choices=[],
                        value=None,  # Start with no selection
                        interactive=True,
                        visible=False  # Hidden by default
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
                """Update report types when company changes"""
                if not company_name:
                    return gr.update(choices=[], value=None, visible=False)  # report_type_dropdown
                
                # Show available reports for the selected company
                report_types = self.get_report_types_for_company(company_name)
                return gr.update(choices=report_types, value=None, visible=True)  # report_type_dropdown
            
            def update_report_content(company_name, report_type):
                """Update report content when company or report type changes"""
                return self.load_report_content(company_name, report_type)
            
            def run_analysis_handler(data_sources_url, search_terms, websites, model):
                """Handle the run analysis button click"""
                if not data_sources_url:
                    return (
                        gr.update(),  # run_analysis_btn
                        gr.update(value="Please provide a data sources URL", visible=True),  # progress_display
                        gr.update(),  # company_dropdown
                        gr.update(choices=[], value=None),  # report_type_dropdown
                        gr.update()   # report_display
                    )
                
                def progress_callback(message):
                    return gr.update(value=message, visible=True)
                
                # Update UI to show progress
                yield (
                    gr.update(interactive=False, value="Running..."),  # run_analysis_btn
                    gr.update(value="Starting analysis...", visible=True),  # progress_display
                    gr.update(),  # company_dropdown
                    gr.update(visible=False),  # report_type_dropdown - hide during analysis
                    gr.update()   # report_display
                )
                
                # Run the analysis in a separate thread
                def run_in_background():
                    return self.run_analysis(data_sources_url, search_terms, websites, model, progress_callback)
                
                import concurrent.futures
                import time
                start_time = time.time()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_background)
                    
                    # Poll for completion
                    while not future.done():
                        time.sleep(1)
                        elapsed = int(time.time() - start_time)
                        mins, secs = divmod(elapsed, 60)
                        yield (
                            gr.update(),  # run_analysis_btn
                            gr.update(value=f"Analysis in progress... {mins:02d}:{secs:02d}"),  # progress_display
                            gr.update(),  # company_dropdown
                            gr.update(visible=False),  # report_type_dropdown - keep hidden during analysis
                            gr.update()   # report_display
                        )
                    
                    result = future.result()
                
                # Calculate total execution time
                total_time = time.time() - start_time
                mins, secs = divmod(int(total_time), 60)
                time_display = f"{mins:02d}:{secs:02d}"
                
                # Refresh company list and re-enable button
                updated_companies = self.get_available_companies()
                
                yield (
                    gr.update(interactive=True, value="Run Analysis"),  # run_analysis_btn
                    gr.update(value=f"Analysis completed in {time_display}! Select a company to view reports.", visible=True),  # progress_display
                    gr.update(choices=updated_companies),  # company_dropdown - refresh with new companies
                    gr.update(visible=False),  # report_type_dropdown - keep hidden until company selected
                    gr.update()   # report_display
                )
            
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
            
            # Run analysis button handler
            run_analysis_btn.click(
                fn=run_analysis_handler,
                inputs=[data_sources_input, search_terms_slider, websites_slider, model_dropdown],
                outputs=[run_analysis_btn, progress_display, company_dropdown, report_type_dropdown, report_display]
            )
            
            # Load initial state (blank)
            demo.load(
                fn=lambda: "",
                inputs=[],
                outputs=[report_display]
            )
        
        return demo


def launch_ui():
    """Launch the due diligence UI"""
    ui = DueDiligenceUI()
    demo = ui.create_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7861,  # Different port to avoid conflicts
        share=False,
        debug=True,
        inbrowser=True
    )


if __name__ == "__main__":
    launch_ui()