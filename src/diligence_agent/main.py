#!/usr/bin/env python
import sys
import warnings

from datetime import datetime

from diligence_agent.crew import DiligenceAgent
from diligence_agent.input_reader import InputReader
from diligence_agent.generate_tasks_yaml import generate_tasks_yaml

from opik.integrations.crewai import track_crewai

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


track_crewai(project_name="diligence-agent")

COMPANY_FILE = "tensorstax.json"  # Options: "baseten.json", "tensorstax.json"

def run():
    """
    Run the crew.
    """
    
    # Read input sources for the specified company
    try:
        reader = InputReader()
        
        # List available companies to help with errors
        available_companies = reader.list_available_companies()
        
        if COMPANY_FILE not in available_companies:
            print(f"Error: Company file '{COMPANY_FILE}' not found.")
            print(f"Available companies: {[c.replace('.json', '') for c in available_companies]}")
            return
        
        # Read the company data
        company_data = reader.read_company_sources(COMPANY_FILE)

        # Generate tasks.yaml with company-specific content
        generate_tasks_yaml()
        
        inputs = {
            'company_name': company_data.company_name,
            'current_year': str(datetime.now().year),
            'current_date': datetime.now().strftime("%Y-%m-%d"),
            'company_sources': [s.model_dump() for s in company_data.company_sources],
            'reference_sources': [s.model_dump() for s in company_data.reference_sources],
        }
        
        print(f"Running diligence analysis for: {company_data.company_name}")
        DiligenceAgent().crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")

