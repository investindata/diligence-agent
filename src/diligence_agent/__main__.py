#!/usr/bin/env python
"""
Entry point for the diligence_agent module.
Suppresses warnings and provides clean output.
"""

import warnings
import sys
import os

# Suppress all warnings before any imports
warnings.filterwarnings("ignore")
os.environ['PYTHONWARNINGS'] = 'ignore'

# Suppress specific warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", message=".*Pydantic.*")
warnings.filterwarnings("ignore", message=".*asyncio.*")
warnings.filterwarnings("ignore", module="pydantic")
warnings.filterwarnings("ignore", module="litellm")

# Now import and run the main module
from diligence_agent.main import run

if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)