import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from diligence_agent.workflow import run_organizer_workflow

if __name__ == "__main__":
    run_organizer_workflow()