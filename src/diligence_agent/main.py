#!/usr/bin/env python
import sys
import warnings
import argparse
import os

# Suppress all warnings before imports to keep output clean
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=SyntaxWarning)
warnings.filterwarnings("ignore", category=UserWarning)
os.environ['PYTHONWARNINGS'] = 'ignore'

from datetime import datetime

from diligence_agent.crew import DiligenceAgent
from diligence_agent.input_reader import InputReader
from diligence_agent.generate_tasks_yaml import generate_tasks_yaml

# from opik.integrations.crewai import track_crewai


# Commented out OPIK tracking - not required for core functionality
# To enable tracking, uncomment and add OPIK_API_KEY to .env
# track_crewai(project_name="diligence-agent")

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
        print(f"Running diligence analysis for: {company_data.company_name}")
        print(f"{'='*60}\n")
        
        result = DiligenceAgent().crew().kickoff(inputs=inputs)
        
        # Move output file to output directory with company name
        exec_summary = Path("executive_summary_and_recommendation.md")
        if exec_summary.exists():
            company_name = company_file.replace('.json', '')
            new_path = output_path / f"{company_name}_executive_summary.md"
            exec_summary.rename(new_path)
            print(f"\n✅ Executive summary saved to: {new_path}")
        
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

