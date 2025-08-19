#!/usr/bin/env python
import sys
import warnings

from datetime import datetime

from diligence_agent.crew import DiligenceAgent
from diligence_agent.input_reader import InputReader

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
        input_sources_text = reader.to_text(COMPANY_FILE)
        
        inputs = {
            'company_name': company_data.company_name,
            'current_year': str(datetime.now().year),
            'input_sources': input_sources_text
        }
        
        print(f"Running diligence analysis for: {company_data.company_name}")
        DiligenceAgent().crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")


def train():
    """
    Train the crew for a given number of iterations.
    """
    
    try:
        reader = InputReader()
        company_data = reader.read_company_sources(COMPANY_FILE)
        
        inputs = {
            "company_name": company_data.company_name,
            'current_year': str(datetime.now().year)
        }
        
        # Get training parameters from command line
        n_iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 1
        filename = sys.argv[2] if len(sys.argv) > 2 else f"{COMPANY_FILE.replace('.json', '')}_training.json"
        
        DiligenceAgent().crew().train(n_iterations=n_iterations, filename=filename, inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        DiligenceAgent().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    """
    
    try:
        reader = InputReader()
        company_data = reader.read_company_sources(COMPANY_FILE)
        
        inputs = {
            "company_name": company_data.company_name,
            "current_year": str(datetime.now().year)
        }
        
        # Get test parameters from command line
        n_iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 1
        eval_llm = sys.argv[2] if len(sys.argv) > 2 else "gpt-4o"
        
        DiligenceAgent().crew().test(n_iterations=n_iterations, eval_llm=eval_llm, inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")
