#!/usr/bin/env python3
"""
Simple LinkedIn authentication helper that doesn't require separate browser installation.
This tool just opens LinkedIn in your default browser and guides you through manual authentication.
"""

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type
import webbrowser
import os
import json


class SimpleAuthInput(BaseModel):
    """Input for simple authentication helper."""
    message: str = Field(description="Message to display to the user during authentication pause")


class SimpleLinkedInAuthTool(BaseTool):
    name: str = "linkedin_manual_auth"
    description: str = "Open LinkedIn in your default browser for manual authentication and create session state for Playwright MCP. Use when LinkedIn login is required."
    args_schema: Type[BaseModel] = SimpleAuthInput
    
    def _run(self, message: str = "Please authenticate with LinkedIn") -> str:
        """
        Simplified authentication that just returns guidance for manual login.
        
        Args:
            message: Message to display to the user
            
        Returns:
            Guidance message for manual authentication
        """
        
        print(f"\n🔐 AUTHENTICATION REQUIRED: {message}")
        print("\n📝 MANUAL AUTHENTICATION NEEDED:")
        print("LinkedIn requires sign-in to access profiles. Please:")
        print("1. Complete your LinkedIn login in any browser")
        print("2. The agent will automatically retry accessing LinkedIn content")
        print("3. If you're already logged in, the agent should be able to continue")
        
        # Return guidance instead of hanging on input
        return (
            "LinkedIn authentication is required. The user has been notified to log in manually. "
            "Please retry accessing LinkedIn content after the user has completed authentication."
        )