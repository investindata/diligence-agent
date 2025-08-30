import gradio as gr
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import os
import base64
import threading
import subprocess
import sys
import json
from datetime import datetime

from diligence_agent.input_reader import InputReader
from diligence_agent.crew import default_model, default_temperature


class DueDiligenceUI:
    """Gradio UI for running analysis and viewing investment reports"""
    
    def __init__(self):
        self.input_reader = InputReader()
        
    def get_available_companies(self) -> List[str]:
        """Get all companies from input_sources directory"""
        try:
            available = self.input_reader.list_available_companies()
            companies = [c.replace('.json', '') for c in available]
            return sorted(companies)
        except Exception as e:
            print(f"Error getting companies: {e}")
            return []
    
    def run_analysis(self, company_name: str, model: str, temperature: float, progress_callback=None) -> str:
        """Run the diligence analysis for a company with specified model and temperature"""
        if not company_name:
            return "No company selected"
        
        try:
            if progress_callback:
                progress_callback("Starting analysis...")
            
            # Run the analysis using subprocess with model and temperature parameters
            cmd = [sys.executable, "-m", "diligence_agent", company_name, "--model", model, "--temperature", str(temperature)]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            output_lines = []
            for line in process.stdout:
                output_lines.append(line.strip())
                if progress_callback:
                    progress_callback(f"Running... (latest: {line.strip()[:100]}...)")
            
            process.wait()
            
            if process.returncode == 0:
                if progress_callback:
                    progress_callback("Analysis completed successfully!")
                return "\n".join(output_lines)
            else:
                if progress_callback:
                    progress_callback(f"Analysis failed with return code {process.returncode}")
                return f"Analysis failed with return code {process.returncode}\n" + "\n".join(output_lines)
                
        except Exception as e:
            error_msg = f"Error running analysis: {str(e)}"
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
        
        # Look in company subdirectories (new structure)
        for session_dir in session_dirs:
            # Convert company name to folder name format (lowercase with underscores)
            company_folder_name = company_name.replace(' ', '_').lower()
            company_dir = session_dir / company_folder_name
            
            if not company_dir.exists():
                continue
                
            # Find all files that match the numbered pattern
            for file_path in company_dir.glob("[0-9]*"):
                filename = file_path.name
                
                # Extract report type from filename
                # Format: {number}_{description}.{ext}
                # e.g., "8_founder_assessment.md" -> "Founder Assessment"
                
                # Extract number and description (e.g., "8_founder_assessment.md" -> "8", "founder_assessment.md")
                number_prefix = ""
                if "_" in filename:
                    parts = filename.split("_", 1)
                    if parts[0].isdigit():
                        number_prefix = parts[0] + ". "
                        name_parts = parts[1]
                    else:
                        name_parts = filename
                else:
                    name_parts = filename
                
                # Remove file extension and convert to readable format
                report_name = name_parts.rsplit(".", 1)[0]  # Remove extension
                report_type = number_prefix + report_name.replace("_", " ").title()
                
                reports.append({
                    "type": report_type,
                    "path": str(file_path),
                    "filename": filename
                })
        
        # Remove duplicates and return most recent for each type
        unique_reports = {}
        for report in reports:
            report_type = report["type"]
            if report_type not in unique_reports:
                unique_reports[report_type] = report
            else:
                # Keep the most recent file
                current_path = Path(unique_reports[report_type]["path"])
                new_path = Path(report["path"])
                if new_path.stat().st_mtime > current_path.stat().st_mtime:
                    unique_reports[report_type] = report
        
        return list(unique_reports.values())
    
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
                    gr.Markdown("### Selection")
                    
                    # Show all companies for selection
                    all_companies = self.get_available_companies()
                    company_dropdown = gr.Dropdown(
                        label="Select Company",
                        choices=all_companies,
                        value=None,  # Start with no selection
                        interactive=True
                    )
                    
                    # Model selection dropdown
                    model_dropdown = gr.Dropdown(
                        label="Select Model",
                        choices=["gpt-4o-mini", "gpt-4.1"],
                        value=default_model,  # Use default from crew.py
                        interactive=True
                    )
                    
                    # Temperature slider
                    temperature_slider = gr.Slider(
                        label="Temperature",
                        minimum=0.0,
                        maximum=2.0,
                        value=default_temperature,  # Use default from crew.py
                        step=0.1,
                        interactive=True
                    )
                    
                    # Add Run Report button
                    run_report_btn = gr.Button(
                        "Run Report",
                        interactive=False,  # Disabled by default
                        variant="primary"
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
            def update_report_types_and_button(company_name):
                """Update button state when company changes - keep dropdown hidden"""
                if not company_name:
                    return (
                        gr.update(choices=[], value=None, visible=False),  # report_type_dropdown
                        gr.update(interactive=False)                       # run_report_btn
                    )
                
                # Keep dropdown hidden until user runs analysis
                return (
                    gr.update(choices=[], value=None, visible=False),  # report_type_dropdown - always hidden initially
                    gr.update(interactive=True)                        # run_report_btn - enable if company selected
                )
            
            def update_report_content(company_name, report_type):
                """Update report content when company or report type changes"""
                return self.load_report_content(company_name, report_type)
            
            def run_analysis_handler(company_name, model, temperature):
                """Handle the run analysis button click"""
                if not company_name:
                    return (
                        gr.update(),  # run_report_btn
                        gr.update(value="Please select a company first", visible=True),  # progress_display
                        gr.update(choices=[], value=None),  # report_type_dropdown
                        gr.update()   # report_display
                    )
                
                def progress_callback(message):
                    return gr.update(value=message, visible=True)
                
                # Update UI to show progress
                yield (
                    gr.update(interactive=False, value="Running..."),  # run_report_btn
                    gr.update(value="Starting analysis...", visible=True),  # progress_display
                    gr.update(visible=False),  # report_type_dropdown - hide during analysis
                    gr.update()   # report_display
                )
                
                # Run the analysis in a separate thread
                def run_in_background():
                    return self.run_analysis(company_name, model, temperature, progress_callback)
                
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
                            gr.update(),  # run_report_btn
                            gr.update(value=f"Analysis in progress... {mins:02d}:{secs:02d}"),  # progress_display
                            gr.update(visible=False),  # report_type_dropdown - keep hidden during analysis
                            gr.update()   # report_display
                        )
                    
                    result = future.result()
                
                # Calculate total execution time
                total_time = time.time() - start_time
                mins, secs = divmod(int(total_time), 60)
                time_display = f"{mins:02d}:{secs:02d}"
                
                # Re-enable button and update report types
                updated_report_types = self.get_report_types_for_company(company_name)
                
                yield (
                    gr.update(interactive=True, value="Run Report"),  # run_report_btn
                    gr.update(value=f"Analysis completed in {time_display}! Reports are now available.", visible=True),  # progress_display
                    gr.update(choices=updated_report_types, value=None, visible=True),  # report_type_dropdown - show after completion
                    gr.update()   # report_display
                )
            
            # Company selection updates report types and button state
            company_dropdown.change(
                fn=update_report_types_and_button,
                inputs=[company_dropdown],
                outputs=[report_type_dropdown, run_report_btn]
            )
            
            # Both company and report type selection update content
            for component in [company_dropdown, report_type_dropdown]:
                component.change(
                    fn=update_report_content,
                    inputs=[company_dropdown, report_type_dropdown],
                    outputs=[report_display]
                )
            
            # Run report button handler
            run_report_btn.click(
                fn=run_analysis_handler,
                inputs=[company_dropdown, model_dropdown, temperature_slider],
                outputs=[run_report_btn, progress_display, report_type_dropdown, report_display]
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