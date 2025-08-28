#!/usr/bin/env python
import sys
import warnings
import argparse
import os

# Suppress all warnings before imports to keep output clean
warnings.filterwarnings("ignore")
os.environ['PYTHONWARNINGS'] = 'ignore'

from datetime import datetime
import time
import json

from diligence_agent.crew import DiligenceAgent
from diligence_agent.input_reader import InputReader
from diligence_agent.generate_tasks_yaml import generate_tasks_yaml

# from opik.integrations.crewai import track_crewai


# Commented out OPIK tracking - not required for core functionality
# To enable tracking, uncomment and add OPIK_API_KEY to .env
# track_crewai(project_name="diligence-agent")

def organize_task_outputs(output_path, company_file):
    """
    Move and organize task outputs to the session directory.
    """
    try:
        from pathlib import Path
        import shutil
        
        company_name = company_file.replace('.json', '')
        task_outputs_src = Path("task_outputs")
        
        if task_outputs_src.exists():
            # Create destination directory
            task_outputs_dest = Path(output_path) / "task_outputs"
            task_outputs_dest.mkdir(exist_ok=True)
            
            # Move and rename files
            for file in task_outputs_src.glob("*"):
                if file.is_file():
                    # Add company name prefix to file
                    new_name = f"{company_name}_{file.name}"
                    dest_file = task_outputs_dest / new_name
                    shutil.move(str(file), str(dest_file))
            
            # Create summary file
            summary_file = task_outputs_dest / f"{company_name}_analysis_summary.md"
            with open(summary_file, 'w') as f:
                f.write(f"# Analysis Summary for {company_name.title()}\n\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
                f.write("## Task Outputs:\n\n")
                f.write("The following intermediate outputs show what analysis drove the final investment decision:\n\n")
                f.write("1. **Data Validation** (`1_data_validation.json`) - Verified facts, completeness scores, red flags\n")
                f.write("2. **Overview Section** (`2_overview.md`) - Company overview and mission\n")
                f.write("3. **Why Interesting** (`3_why_interesting.md`) - Investment thesis\n")
                f.write("4. **Product Analysis** (`4_product.md`) - Product deep dive\n")
                f.write("5. **Market Analysis** (`5_market.md`) - TAM and market dynamics\n")
                f.write("6. **Competitive Landscape** (`6_competitive.md`) - Competition analysis\n")
                f.write("7. **Team Section** (`7_team.md`) - Team backgrounds\n")
                f.write("8. **Founder Assessment** (`8_founder_assessment.md`) - Founder quality rating (A/B/C) and analysis\n")
                f.write("9. **Full Report** (`9_full_report.md`) - Compiled investment report\n")
                f.write("10. **Executive Summary** (`10_executive_summary.md`) - Final investment recommendation\n\n")
                f.write("## How to Use These Outputs:\n\n")
                f.write("- Review the **Data Validation** to understand what facts were verified\n")
                f.write("- Check the **Founder Assessment** for the detailed founder rating\n")
                f.write("- Read individual sections to understand specific concerns\n")
                f.write("- The **Executive Summary** synthesizes all findings into the final recommendation\n")
            
            print(f"📂 Task outputs organized in: {task_outputs_dest}/")
            
    except Exception as e:
        print(f"Note: Could not organize task outputs: {e}")

def save_task_outputs(crew, output_path, company_file):
    """
    Save all task outputs to separate files for analysis.
    This helps understand what drove the final investment decision.
    """
    try:
        from pathlib import Path
        
        # Create task_outputs subdirectory
        task_output_dir = Path(output_path) / "task_outputs"
        task_output_dir.mkdir(exist_ok=True)
        
        company_name = company_file.replace('.json', '')
        
        # Define task names and their output files
        task_mapping = {
            'data_organizer_task': f'{company_name}_1_data_validation.json',
            'overview_section_writer_task': f'{company_name}_2_overview.md',
            'why_interesting_section_writer_task': f'{company_name}_3_why_interesting.md',
            'product_section_writer_task': f'{company_name}_4_product.md',
            'market_section_writer_task': f'{company_name}_5_market.md',
            'competitive_landscape_section_writer_task': f'{company_name}_6_competitive.md',
            'team_section_writer_task': f'{company_name}_7_team.md',
            'founder_assessment_task': f'{company_name}_8_founder_assessment.md',
            'report_writer_task': f'{company_name}_9_full_report.md',
            'executive_summary_task': f'{company_name}_10_executive_summary.md'
        }
        
        # Try to access task results if available
        if hasattr(crew, 'tasks'):
            for task in crew.tasks:
                if hasattr(task, 'output') and task.output:
                    # Get task name from config
                    task_name = None
                    if hasattr(task, 'config') and 'agent' in task.config:
                        agent_name = str(task.config['agent'])
                        # Map agent to task name
                        if 'Data Validator' in agent_name:
                            task_name = 'data_organizer_task'
                        elif 'Section Writer' in agent_name:
                            # Determine which section based on description
                            if hasattr(task, 'config') and 'description' in task.config:
                                desc = task.config['description'].lower()
                                if 'overview' in desc:
                                    task_name = 'overview_section_writer_task'
                                elif 'interesting' in desc:
                                    task_name = 'why_interesting_section_writer_task'
                                elif 'product' in desc:
                                    task_name = 'product_section_writer_task'
                                elif 'market' in desc:
                                    task_name = 'market_section_writer_task'
                                elif 'competitive' in desc:
                                    task_name = 'competitive_landscape_section_writer_task'
                                elif 'team' in desc:
                                    task_name = 'team_section_writer_task'
                        elif 'Founder' in agent_name:
                            task_name = 'founder_assessment_task'
                        elif 'Report Writer' in agent_name:
                            task_name = 'report_writer_task'
                        elif 'Investment' in agent_name or 'Decision' in agent_name:
                            task_name = 'executive_summary_task'
                    
                    # Save the output
                    if task_name and task_name in task_mapping:
                        output_file = task_output_dir / task_mapping[task_name]
                        
                        # Convert output to string
                        output_content = str(task.output)
                        
                        # Save as JSON for data validation task
                        if task_name == 'data_organizer_task':
                            try:
                                # Try to parse as JSON
                                json_data = json.loads(output_content) if isinstance(output_content, str) else output_content
                                with open(output_file, 'w') as f:
                                    json.dump(json_data, f, indent=2)
                            except:
                                # If not valid JSON, save as text
                                with open(output_file, 'w') as f:
                                    f.write(output_content)
                        else:
                            # Save as markdown for other tasks
                            with open(output_file, 'w') as f:
                                f.write(output_content)
        
        # Create a summary file listing all outputs
        summary_file = task_output_dir / f"{company_name}_task_summary.md"
        with open(summary_file, 'w') as f:
            f.write(f"# Task Outputs Summary for {company_name.title()}\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write("## Task Outputs Saved:\n\n")
            f.write("These intermediate outputs show what analysis drove the final investment decision:\n\n")
            f.write("1. **Data Validation** - Verified facts, completeness scores, red flags\n")
            f.write("2. **Overview Section** - Company overview and mission\n")
            f.write("3. **Why Interesting** - Investment thesis\n")
            f.write("4. **Product Analysis** - Product deep dive\n")
            f.write("5. **Market Analysis** - TAM and market dynamics\n")
            f.write("6. **Competitive Landscape** - Competition analysis\n")
            f.write("7. **Team Section** - Team backgrounds\n")
            f.write("8. **Founder Assessment** - Founder quality rating and analysis\n")
            f.write("9. **Full Report** - Compiled investment report\n")
            f.write("10. **Executive Summary** - Final investment recommendation\n")
        
        print(f"📁 Task outputs saved to: {task_output_dir}/")
        
    except Exception as e:
        print(f"Note: Could not save all task outputs: {e}")
        # Don't fail the main process if output saving fails

def get_user_selection(available_companies):
    """
    Interactive menu for selecting companies to analyze.
    """
    print("\n" + "="*60)
    print("DILIGENCE AGENT - Company Selection")
    print("="*60)
    print("\nAvailable companies:")
    
    # Display companies with numbers
    company_list = []
    for i, company_file in enumerate(available_companies, 1):
        company_name = company_file.replace('.json', '').title()
        company_list.append(company_file)
        print(f"  {i}. {company_name}")
    
    print(f"  {len(company_list) + 1}. All companies")
    print(f"  {len(company_list) + 2}. Exit")
    
    while True:
        try:
            print("\nSelect option(s):")
            print("  - Single number (e.g., '1')")
            print("  - Multiple numbers separated by commas (e.g., '1,2')")
            print("  - Range (e.g., '1-3')")
            
            selection = input("\nYour choice: ").strip()
            
            if not selection:
                print("❌ No selection made. Please try again.")
                continue
            
            # Parse selection
            selected_indices = []
            
            # Check for "all" option
            if selection == str(len(company_list) + 1):
                return company_list
            
            # Check for exit
            if selection == str(len(company_list) + 2):
                print("Exiting...")
                sys.exit(0)
            
            # Parse comma-separated or range
            if ',' in selection:
                # Multiple selections
                for part in selection.split(','):
                    part = part.strip()
                    if '-' in part:
                        # Range within comma-separated
                        start, end = part.split('-')
                        for i in range(int(start), int(end) + 1):
                            selected_indices.append(i)
                    else:
                        selected_indices.append(int(part))
            elif '-' in selection:
                # Range selection
                start, end = selection.split('-')
                for i in range(int(start), int(end) + 1):
                    selected_indices.append(i)
            else:
                # Single selection
                selected_indices.append(int(selection))
            
            # Validate indices and get companies
            selected_companies = []
            for idx in selected_indices:
                if 1 <= idx <= len(company_list):
                    selected_companies.append(company_list[idx - 1])
                else:
                    print(f"❌ Invalid selection: {idx}")
                    raise ValueError
            
            if selected_companies:
                print(f"\n✅ Selected: {[c.replace('.json', '').title() for c in selected_companies]}")
                return selected_companies
            
        except (ValueError, IndexError):
            print("❌ Invalid input. Please enter valid number(s).")
        except KeyboardInterrupt:
            print("\n\nCancelled by user.")
            sys.exit(0)

def run_company_analysis(company_file: str, output_dir: str = "output"):
    """
    Run the crew for a specific company.
    """
    try:
        from pathlib import Path
        
        # Ensure output directory exists
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Create task_outputs directory for intermediate results
        task_outputs_path = Path("task_outputs")
        task_outputs_path.mkdir(exist_ok=True)
        
        reader = InputReader()
        
        # List available companies to help with errors
        available_companies = reader.list_available_companies()
        
        if company_file not in available_companies:
            print(f"Error: Company file '{company_file}' not found.")
            print(f"Available companies: {[c.replace('.json', '') for c in available_companies]}")
            return False
        
        # Read the company data
        company_data = reader.read_company_sources(company_file)

        # Generate tasks.yaml with company-specific content
        generate_tasks_yaml()
        
        inputs = {
            'company_name': company_data.company_name,
            'current_year': str(datetime.now().year),
            'current_date': datetime.now().strftime("%Y-%m-%d"),
            'company_sources': [s.model_dump() for s in company_data.company_sources],
            'reference_sources': [s.model_dump() for s in company_data.reference_sources],
        }
        
        print(f"\n{'='*60}")
        print(f"🚀 Starting diligence analysis for: {company_data.company_name}")
        print(f"{'='*60}")
        print(f"")
        print(f"📊 Analysis Pipeline (10 tasks):")
        print(f"   Phase 1: Data Validation & Verification")
        print(f"   Phase 2: Parallel Analysis (7 concurrent tasks)")
        print(f"           - 6 Report Sections")
        print(f"           - Founder Assessment")
        print(f"   Phase 3: Report Compilation")
        print(f"   Phase 4: Executive Summary & Investment Decision")
        print(f"")
        print(f"⏱️  Estimated time: 10-15 minutes")
        print(f"💡 Tip: Look for task IDs and ✅ symbols to track progress")
        print(f"{'='*60}\n")
        
        # Start timer
        start_time = time.time()
        
        # Run the crew
        crew_instance = DiligenceAgent()
        crew = crew_instance.crew()
        result = crew.kickoff(inputs=inputs)
        
        # Calculate total time
        end_time = time.time()
        duration = end_time - start_time
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        
        print(f"\n{'='*60}")
        print(f"✅ Analysis Complete!")
        print(f"⏱️  Total time: {minutes:02d}:{seconds:02d}")
        print(f"{'='*60}")
        
        # Move task outputs to session directory
        organize_task_outputs(output_path, company_file)
        
        # Move output files to output directory with company name
        company_name = company_file.replace('.json', '')
        
        # Move executive summary
        exec_summary = Path("executive_summary_and_recommendation.md")
        if exec_summary.exists():
            new_path = output_path / f"{company_name}_executive_summary.md"
            exec_summary.rename(new_path)
            print(f"\n✅ Executive summary saved to: {new_path}")
        
        # Move full due diligence report
        full_report = Path("full_due_diligence_report.md")
        if full_report.exists():
            new_full_report_path = output_path / f"{company_name}_full_due_diligence_report.md"
            full_report.rename(new_full_report_path)
            print(f"\n📄 Full report saved to: {new_full_report_path}")
        
        return True
        
    except Exception as e:
        print(f"Error analyzing {company_file}: {e}")
        return False

def run():
    """
    Run the crew with command-line arguments support.
    """
    from pathlib import Path
    
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Diligence Agent - AI-powered investment due diligence',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                     # Interactive mode - select companies from menu
  %(prog)s --list             # List available companies
  %(prog)s tensorstax         # Analyze single company
  %(prog)s tensorstax baseten # Analyze multiple companies
  %(prog)s --all              # Analyze all available companies
        """
    )
    
    parser.add_argument('companies', nargs='*', 
                       help='Company name(s) to analyze (without .json extension)')
    parser.add_argument('--list', '-l', action='store_true',
                       help='List available companies and exit')
    parser.add_argument('--all', '-a', action='store_true',
                       help='Analyze all available companies')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Force interactive mode even with arguments')
    
    args = parser.parse_args()
    
    # Get available companies
    reader = InputReader()
    available = reader.list_available_companies()
    
    # Handle --list flag
    if args.list:
        print("\nAvailable companies:")
        for company in available:
            print(f"  - {company.replace('.json', '')}")
        sys.exit(0)
    
    # Determine which companies to analyze
    if args.all:
        companies = available
        print(f"\n✅ Analyzing all companies: {[c.replace('.json', '') for c in companies]}")
    elif args.companies and not args.interactive:
        # Command-line specified companies
        companies = []
        for company_name in args.companies:
            # Add .json if not present
            if not company_name.endswith('.json'):
                company_name = f"{company_name}.json"
            
            if company_name in available:
                companies.append(company_name)
            else:
                print(f"❌ Company '{company_name.replace('.json', '')}' not found.")
                print(f"Available: {[c.replace('.json', '') for c in available]}")
                sys.exit(1)
        
        if companies:
            print(f"\n✅ Selected companies: {[c.replace('.json', '') for c in companies]}")
    else:
        # Interactive mode
        companies = get_user_selection(available)
    
    print(f"\n{'='*60}")
    print(f"DILIGENCE AGENT - ANALYSIS SESSION")
    print(f"{'='*60}")
    print(f"Companies to analyze: {[c.replace('.json', '') for c in companies]}")
    print(f"Output directory: output/")
    print(f"{'='*60}\n")
    
    # Create output directory with timestamp for this session
    from pathlib import Path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = f"output/session_{timestamp}"
    Path(session_dir).mkdir(parents=True, exist_ok=True)
    
    results = {}
    
    # Analyze each company
    for i, company_file in enumerate(companies, 1):
        if len(companies) > 1:
            print(f"\n[{i}/{len(companies)}] Processing {company_file}...")
        
        success = run_company_analysis(company_file, session_dir)
        company_name = company_file.replace('.json', '')
        results[company_name] = success
    
    # Print summary if multiple companies
    if len(companies) > 1:
        print(f"\n{'='*60}")
        print("ANALYSIS COMPLETE - SUMMARY")
        print(f"{'='*60}")
        
        for company, success in results.items():
            status = "✅ Success" if success else "❌ Failed"
            print(f"{status} - {company}")
            if success:
                exec_file = Path(session_dir) / f"{company}_executive_summary.md"
                if exec_file.exists():
                    print(f"    → Executive summary: {exec_file}")
        
        # Create combined summary file in session directory
        summary_path = Path(session_dir) / "ALL_COMPANIES_SUMMARY.md"
        with open(summary_path, "w") as f:
            f.write("# Multi-Company Analysis Summary\n\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            
            for company, success in results.items():
                f.write(f"## {company.title()}\n")
                f.write(f"- Status: {'✅ Completed' if success else '❌ Failed'}\n")
                
                exec_file = f"{company}_executive_summary.md"
                exec_path = Path(session_dir) / exec_file
                if exec_path.exists():
                    f.write(f"- [View Executive Summary](./{exec_file})\n")
                f.write("\n")
        
        print(f"\n📊 Combined summary saved to: {summary_path}")
    
    # Final message with output location
    print(f"\n📁 All outputs saved to: {session_dir}/")
    
    # Clean shutdown to avoid asyncio warnings
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.close()
    except:
        pass

