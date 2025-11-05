#!/usr/bin/env python3
"""
Entry point for Hugging Face Spaces deployment.
This script sets up the Python path and launches the UI.
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path for proper imports
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

# Now we can import and run the UI
from diligence_agent.app import launch_ui

if __name__ == "__main__":
    launch_ui()