#!/usr/bin/env python
"""
Clean launcher for the diligence agent.
Run with: python analyze.py
"""

def suppress_all_warnings():
    """Suppress all warnings before any imports."""
    import warnings
    import os
    import sys
    
    # Suppress warnings at every level
    warnings.filterwarnings("ignore")
    os.environ['PYTHONWARNINGS'] = 'ignore'
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    
    # Suppress stderr during imports
    import contextlib
    import io
    
    class SuppressOutput:
        def __enter__(self):
            self._original_stderr = sys.stderr
            sys.stderr = io.StringIO()
            return self
            
        def __exit__(self, *args):
            sys.stderr = self._original_stderr
    
    return SuppressOutput()

# Suppress warnings before any imports
suppress_all_warnings()

import sys
import os

# Add the src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Now import and run with warning suppression
with suppress_all_warnings():
    import asyncio
    import logging
    
    # Set up asyncio to avoid warnings
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Suppress all loggers
    logging.getLogger().setLevel(logging.ERROR)
    for logger_name in ['asyncio', 'pydantic', 'litellm', 'httpx', 'httpcore']:
        logging.getLogger(logger_name).setLevel(logging.ERROR)

# Import and run the main program
from diligence_agent.main import run

if __name__ == "__main__":
    try:
        with suppress_all_warnings():
            run()
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(0)
    except SystemExit:
        pass  # Normal exit
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
    finally:
        # Clean shutdown
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if not loop.is_closed():
                loop.close()
        except:
            pass