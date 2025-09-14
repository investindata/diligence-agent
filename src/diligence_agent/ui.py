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
from diligence_agent.tools.google_doc_processor import GoogleDocProcessor
from diligence_agent.schemas import CompanyDataSources
from diligence_agent.utils import extract_structured_output
from diligence_agent.agents import organizer_agent


class DueDiligenceUI:
    """Gradio UI for running analysis and viewing investment reports"""
    
    def __init__(self):
        self.company_metadata_dir = Path("company_metadata")
        self.company_metadata_dir.mkdir(exist_ok=True)
        self.companies_index_file = self.company_metadata_dir / "companies_index.json"
        self.section_progress = {}  # Track section progress for UI updates
        
    def get_available_companies(self) -> List[str]:
        """Get all stored companies from company_metadata directory"""
        try:
            if not self.companies_index_file.exists():
                return ["New Company"]
            
            with open(self.companies_index_file, 'r') as f:
                companies_data = json.load(f)
            
            companies = list(companies_data.keys())
            companies.append("New Company")
            return companies
        except Exception as e:
            print(f"Error getting companies: {e}")
            return ["New Company"]
    
    def run_analysis(self, data_sources_url: str, num_search_terms: int = 5, num_websites: int = 10, model: str = "gpt-4.1-mini", progress_callback=None) -> str:
        """Run the diligence analysis using the flow system with data sources URL"""
        if not data_sources_url:
            return "No data sources URL provided"
        
        try:
            if progress_callback:
                progress_callback("Starting flow-based analysis...")
            
            # Create section progress callback that updates UI
            def section_progress_callback(section_name: str, status: str):
                self.update_section_progress(section_name, status)
                # This callback will be called for real-time updates during polling
                if hasattr(self, '_current_section_update_callback'):
                    self._current_section_update_callback()
            
            # Run the analysis using the flow system directly
            async def run_flow():
                return await kickoff(
                    data_sources_file=data_sources_url,
                    num_search_terms=num_search_terms,
                    num_websites=num_websites,
                    model=model,
                    progress_callback=section_progress_callback
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
    
    def save_company_metadata(self, company_name: str, data_sources_url: str) -> bool:
        """Save company metadata to files"""
        try:
            # Load or create companies index
            if self.companies_index_file.exists():
                with open(self.companies_index_file, 'r') as f:
                    companies_index = json.load(f)
            else:
                companies_index = {}
            
            # Create individual company file
            company_file = self.company_metadata_dir / f"{company_name.lower().replace(' ', '_')}.json"
            
            now = datetime.now().isoformat()
            company_data = {
                "name": company_name,
                "data_sources_url": data_sources_url,
                "created_at": now,
                "last_used": now,
                "analysis_count": 1
            }
            
            # Update existing company or create new
            if company_name in companies_index:
                # Load existing data and update
                with open(company_file, 'r') as f:
                    existing_data = json.load(f)
                company_data["created_at"] = existing_data["created_at"]
                company_data["analysis_count"] = existing_data.get("analysis_count", 0) + 1
            
            # Save individual company file
            with open(company_file, 'w') as f:
                json.dump(company_data, f, indent=2)
            
            # Update companies index
            companies_index[company_name] = {
                "file": str(company_file),
                "last_used": now
            }
            
            # Save companies index
            with open(self.companies_index_file, 'w') as f:
                json.dump(companies_index, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving company metadata: {e}")
            return False
    
    def get_company_data_sources_url(self, company_name: str) -> Optional[str]:
        """Get data sources URL for a company"""
        try:
            if company_name == "New Company":
                return None
                
            company_file = self.company_metadata_dir / f"{company_name.lower().replace(' ', '_')}.json"
            if not company_file.exists():
                return None
                
            with open(company_file, 'r') as f:
                company_data = json.load(f)
                
            return company_data.get("data_sources_url")
        except Exception as e:
            print(f"Error getting company data sources URL: {e}")
            return None
    
    async def extract_company_name_from_url(self, data_sources_url: str) -> Optional[str]:
        """Extract company name from data sources URL using LLM"""
        try:
            # Get raw content from Google Doc
            google_doc_processor = GoogleDocProcessor()
            raw_data_sources = google_doc_processor._run(data_sources_url).strip()
            
            # Use LLM to extract company name
            query = (
                f"Parse the following Google Doc content and extract both the company name and data sources.\n\n"
                f"Raw content:\n{raw_data_sources}\n\n"
                f"Extract:\n"
                f"1. The company name (look for patterns like 'Company name: X' or similar)\n"
                f"2. All data sources organized into the required structure\n\n"
                f"Return both the company name and structured data sources."
            )
            
            result = await organizer_agent.kickoff_async(query, response_format=CompanyDataSources)
            company_data_sources = extract_structured_output(result, CompanyDataSources)
            
            if company_data_sources.company_name:
                return company_data_sources.company_name.strip()
            else:
                return None
                
        except Exception as e:
            print(f"Error extracting company name: {e}")
            return None
    
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
    
    def update_section_progress(self, section_name: str, status: str):
        """Update progress for a specific section"""
        self.section_progress[section_name] = status
    
    def format_section_progress(self) -> str:
        """Format section progress as markdown list"""
        if not self.section_progress:
            return ""
        
        # Import here to avoid circular imports
        from diligence_agent.flow import DiligenceState
        
        # Get the actual sections from DiligenceState
        default_state = DiligenceState()
        sections_in_order = default_state.sections_to_run
        
        # Map status to emoji
        status_emoji = {
            "pending": "⏳",
            "in_progress": "🔄",
            "completed": "✅"
        }
        
        lines = []
        for section in sections_in_order:
            if section in self.section_progress:
                status = self.section_progress[section]
                emoji = status_emoji.get(status, "❓")
                lines.append(f"{emoji} {section}")
        
        return "\n".join(lines) if lines else ""
    
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
                    gr.Markdown("### Company Selection")
                    
                    # Company selection dropdown
                    all_companies = self.get_available_companies()
                    company_dropdown = gr.Dropdown(
                        label="Select Company",
                        choices=all_companies,
                        value=None,
                        interactive=True
                    )
                    
                    # Data Sources URL input (hidden by default)
                    data_sources_input = gr.Textbox(
                        label="Data Sources URL",
                        placeholder="Paste Google Doc URL containing company data sources...",
                        lines=2,
                        interactive=True,
                        visible=False
                    )
                    
                    # Process URL button (hidden by default)
                    process_url_btn = gr.Button(
                        "Process URL",
                        interactive=True,
                        variant="secondary",
                        visible=False
                    )
                    
                    # Status message for URL processing
                    url_status = gr.Textbox(
                        label="Status",
                        value="",
                        interactive=False,
                        visible=False
                    )
                    
                    gr.Markdown("### Research Parameters")

                    model_dropdown = gr.Dropdown(
                        label="Model",
                        choices=["gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1"],
                        value="gpt-4.1-mini",
                        interactive=True
                    )
                    
                    search_terms_slider = gr.Slider(
                        label="Search Terms",
                        minimum=1,
                        maximum=20,
                        value=5,
                        step=1,
                        interactive=True
                    )
                    
                    websites_slider = gr.Slider(
                        label="Websites per Search",
                        minimum=1,
                        maximum=50,
                        value=10,
                        step=1,
                        interactive=True
                    )
                    
                    # Add Run Analysis button
                    run_analysis_btn = gr.Button(
                        "Run Analysis",
                        interactive=False,  # Disabled until company selected
                        variant="primary"
                    )
                    
                    gr.Markdown("### View Reports")
                    
                    # Report selection will use the same company dropdown from above
                    
                    # Progress display
                    # Section progress display
                    section_progress_display = gr.Markdown(
                        value="",
                        visible=False,
                        label="Analysis Progress"
                    )
                    
                    # Progress status message
                    progress_display = gr.Textbox(
                        label="Status",
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
            def handle_company_selection(company_name):
                """Handle company selection - show/hide data sources input"""
                if not company_name:
                    return (
                        gr.update(visible=False),  # data_sources_input
                        gr.update(visible=False),  # process_url_btn
                        gr.update(visible=False),  # url_status
                        gr.update(interactive=False),  # run_analysis_btn
                        gr.update(choices=[], value=None, visible=False)  # report_type_dropdown
                    )
                
                if company_name == "New Company":
                    return (
                        gr.update(visible=True, value=""),  # data_sources_input
                        gr.update(visible=True),  # process_url_btn  
                        gr.update(visible=False),  # url_status
                        gr.update(interactive=False),  # run_analysis_btn
                        gr.update(choices=[], value=None, visible=False)  # report_type_dropdown
                    )
                else:
                    # Existing company - show reports and enable analysis
                    report_types = self.get_report_types_for_company(company_name)
                    return (
                        gr.update(visible=False),  # data_sources_input
                        gr.update(visible=False),  # process_url_btn
                        gr.update(visible=False),  # url_status
                        gr.update(interactive=True),  # run_analysis_btn
                        gr.update(choices=report_types, value=None, visible=True)  # report_type_dropdown
                    )
            
            async def process_new_company_url(data_sources_url):
                """Process URL for new company and extract company name"""
                if not data_sources_url:
                    yield (
                        gr.update(),  # company_dropdown
                        gr.update(value="Please enter a data sources URL", visible=True),  # url_status
                        gr.update(interactive=False),  # run_analysis_btn
                        gr.update(choices=[], value=None, visible=False)  # report_type_dropdown
                    )
                    return
                
                # Show processing status
                yield (
                    gr.update(),  # company_dropdown
                    gr.update(value="Extracting company name...", visible=True),  # url_status
                    gr.update(interactive=False),  # run_analysis_btn
                    gr.update(choices=[], value=None, visible=False)  # report_type_dropdown
                )
                
                try:
                    # Extract company name using LLM
                    company_name = await self.extract_company_name_from_url(data_sources_url)
                    
                    if company_name:
                        # Save company metadata
                        if self.save_company_metadata(company_name, data_sources_url):
                            # Update dropdown choices and select the new company
                            updated_companies = self.get_available_companies()
                            yield (
                                gr.update(choices=updated_companies, value=company_name),  # company_dropdown
                                gr.update(value=f"Company '{company_name}' added successfully!", visible=True),  # url_status
                                gr.update(interactive=True),  # run_analysis_btn
                                gr.update(choices=[], value=None, visible=False)  # report_type_dropdown
                            )
                        else:
                            yield (
                                gr.update(),  # company_dropdown
                                gr.update(value="Error saving company data", visible=True),  # url_status
                                gr.update(interactive=False),  # run_analysis_btn
                                gr.update(choices=[], value=None, visible=False)  # report_type_dropdown
                            )
                    else:
                        yield (
                            gr.update(),  # company_dropdown
                            gr.update(value="Could not extract company name from URL", visible=True),  # url_status
                            gr.update(interactive=False),  # run_analysis_btn
                            gr.update(choices=[], value=None, visible=False)  # report_type_dropdown
                        )
                        
                except Exception as e:
                    yield (
                        gr.update(),  # company_dropdown
                        gr.update(value=f"Error processing URL: {str(e)}", visible=True),  # url_status
                        gr.update(interactive=False),  # run_analysis_btn
                        gr.update(choices=[], value=None, visible=False)  # report_type_dropdown
                    )
            
            def update_report_types(company_name):
                """Update report types dropdown when company is selected"""
                if company_name and company_name != "New Company":
                    report_types = self.get_report_types_for_company(company_name)
                    return gr.update(choices=report_types, value=None, visible=True)
                else:
                    return gr.update(choices=[], value=None, visible=False)
            
            def update_report_content(company_name, report_type):
                """Update report content when company or report type changes"""
                return self.load_report_content(company_name, report_type)
            
            def run_analysis_handler(company_name, search_terms, websites, model):
                """Handle the run analysis button click"""
                if not company_name or company_name == "New Company":
                    return (
                        gr.update(),  # run_analysis_btn
                        gr.update(value="", visible=False),  # section_progress_display
                        gr.update(value="Please select a company to run analysis", visible=True),  # progress_display
                        gr.update(),  # company_dropdown
                        gr.update(choices=[], value=None),  # report_type_dropdown
                        gr.update()   # report_display
                    )
                
                # Get the data sources URL for the selected company
                data_sources_url = self.get_company_data_sources_url(company_name)
                if not data_sources_url:
                    return (
                        gr.update(),  # run_analysis_btn
                        gr.update(value="", visible=False),  # section_progress_display
                        gr.update(value="No data sources URL found for selected company", visible=True),  # progress_display
                        gr.update(),  # company_dropdown
                        gr.update(choices=[], value=None),  # report_type_dropdown
                        gr.update()   # report_display
                    )
                
                # Reset section progress for new analysis
                self.section_progress = {}
                
                def progress_callback(message):
                    return gr.update(value=message, visible=True)
                
                # Update UI to show progress
                yield (
                    gr.update(interactive=False, value="Running..."),  # run_analysis_btn
                    gr.update(value="", visible=True),  # section_progress_display
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
                    
                    # Poll for completion and update section progress
                    while not future.done():
                        time.sleep(1)
                        elapsed = int(time.time() - start_time)
                        mins, secs = divmod(elapsed, 60)
                        
                        # Get current section progress
                        section_progress_md = self.format_section_progress()
                        
                        yield (
                            gr.update(),  # run_analysis_btn
                            gr.update(value=section_progress_md, visible=True if section_progress_md else False),  # section_progress_display
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
                
                # Get final section progress
                final_section_progress = self.format_section_progress()
                
                yield (
                    gr.update(interactive=True, value="Run Analysis"),  # run_analysis_btn
                    gr.update(value=final_section_progress, visible=True if final_section_progress else False),  # section_progress_display
                    gr.update(value=f"Analysis completed in {time_display}! Select a company to view reports.", visible=True),  # progress_display
                    gr.update(choices=updated_companies),  # company_dropdown - refresh with new companies
                    gr.update(visible=False),  # report_type_dropdown - keep hidden until company selected
                    gr.update()   # report_display
                )
            
            # Process URL button handler
            process_url_btn.click(
                fn=process_new_company_url,
                inputs=[data_sources_input],
                outputs=[company_dropdown, url_status, run_analysis_btn, report_type_dropdown]
            )
            
            # Company selection updates data sources input visibility
            company_dropdown.change(
                fn=handle_company_selection,
                inputs=[company_dropdown],
                outputs=[data_sources_input, process_url_btn, url_status, run_analysis_btn, report_type_dropdown]
            )
            
            # Company selection also updates report types
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
                inputs=[company_dropdown, search_terms_slider, websites_slider, model_dropdown],
                outputs=[run_analysis_btn, section_progress_display, progress_display, company_dropdown, report_type_dropdown, report_display]
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