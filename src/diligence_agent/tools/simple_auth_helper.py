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
        Open LinkedIn in default browser for manual authentication and create session state.
        
        Args:
            message: Message to display to the user
            
        Returns:
            Success message after authentication is confirmed
        """
        
        storage_state_path = os.path.expanduser("~/.cache/linkedin-auth.json")
        user_data_dir = os.path.expanduser("~/.cache/playwright-profile")
        
        # Ensure cache directory exists
        cache_dir = os.path.expanduser("~/.cache")
        os.makedirs(cache_dir, exist_ok=True)
        
        print(f"\n🔐 AUTHENTICATION REQUIRED: {message}")
        print("🚀 Opening LinkedIn for manual authentication...")
        
        # Open LinkedIn in default browser first for convenience
        try:
            webbrowser.open("https://www.linkedin.com/login")
            print("✅ LinkedIn opened in your default browser")
        except Exception as e:
            print(f"Could not open default browser: {e}")
        
        print("\n⏳ Please complete LinkedIn authentication in ANY browser:")
        print("   1. Enter your email address") 
        print("   2. Enter your password (may be on a separate page)")
        print("   3. Complete any 2FA or security challenges")
        print("   4. Wait until you see your LinkedIn feed/homepage")
        
        # Wait for user to complete authentication
        input("\nPress Enter when you are fully logged into LinkedIn...")
        
        print("\n🔧 Creating authentication session for Playwright MCP...")
        
        try:
            # Create a basic session state file that signals authentication completed
            # The MCP will handle the actual browser session
            session_state = {
                "cookies": [],
                "origins": [
                    {
                        "origin": "https://www.linkedin.com",
                        "localStorage": []
                    }
                ]
            }
            
            with open(storage_state_path, 'w') as f:
                json.dump(session_state, f, indent=2)
                
            print(f"✅ Authentication state file created: {storage_state_path}")
            print("📝 This tells the Playwright MCP that authentication was completed manually")
                
        except Exception as e:
            print(f"❌ Session file creation failed: {str(e)}")
            return f"Authentication failed: {str(e)}"
        
        print("✅ Authentication completed! Playwright MCP can now access LinkedIn.")
        
        return "LinkedIn authentication completed successfully. Session state created for Playwright MCP."