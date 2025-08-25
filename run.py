#!/usr/bin/env python
"""
Clean runner for the diligence agent that suppresses warnings.
"""

import sys
import os
import warnings

# Set up the cleanest possible environment
os.environ['PYTHONWARNINGS'] = 'ignore'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

# Suppress all warnings
warnings.simplefilter("ignore")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# Fix asyncio event loop warning by creating one if it doesn't exist
import asyncio
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# Suppress logging warnings
import logging
logging.getLogger('asyncio').setLevel(logging.ERROR)
logging.getLogger('pydantic').setLevel(logging.ERROR)
logging.getLogger('litellm').setLevel(logging.ERROR)
logging.getLogger('httpx').setLevel(logging.ERROR)
logging.getLogger('httpcore').setLevel(logging.ERROR)

# Redirect stderr temporarily during imports
import contextlib
import io
stderr = io.StringIO()

with contextlib.redirect_stderr(stderr):
    # Import modules that might generate warnings
    try:
        import litellm
    except:
        pass

# Now run the main program
if __name__ == "__main__":
    from diligence_agent.main import run
    try:
        run()
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(0)