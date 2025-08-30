#!/usr/bin/env python3
"""
Google OAuth2 Setup Script

This script handles the one-time setup process to authenticate with Google Drive API.
It will:
1. Open your browser for Google login
2. Ask for permission to access your Google Drive
3. Generate a refresh token and save it to .env

Run this once after setting up your Google Cloud Console credentials.
"""

import os
import sys
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Scopes needed for Google Drive access
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',  # Read-only access to Google Drive
    'https://www.googleapis.com/auth/documents.readonly'  # Read-only access to Google Docs
]

def load_env_variables():
    """Load environment variables from .env file"""
    env_path = Path('.env')
    if not env_path.exists():
        print("❌ Error: .env file not found!")
        print("Make sure you're running this from the project root directory.")
        sys.exit(1)
    
    env_vars = {}
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value
    
    return env_vars

def update_env_file(refresh_token):
    """Update the .env file with the refresh token"""
    env_path = Path('.env')
    
    # Read current content
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # Update the GOOGLE_REFRESH_TOKEN line
    updated_lines = []
    token_updated = False
    
    for line in lines:
        if line.startswith('GOOGLE_REFRESH_TOKEN='):
            updated_lines.append(f'GOOGLE_REFRESH_TOKEN={refresh_token}\n')
            token_updated = True
        else:
            updated_lines.append(line)
    
    # If token line wasn't found, add it
    if not token_updated:
        updated_lines.append(f'GOOGLE_REFRESH_TOKEN={refresh_token}\n')
    
    # Write back to file
    with open(env_path, 'w') as f:
        f.writelines(updated_lines)

def main():
    print("🔑 Google OAuth2 Setup for Diligence Agent")
    print("=" * 50)
    
    # Load environment variables
    env_vars = load_env_variables()
    
    # Check if required credentials are set
    client_id = env_vars.get('GOOGLE_CLIENT_ID', '').strip()
    client_secret = env_vars.get('GOOGLE_CLIENT_SECRET', '').strip()
    
    if not client_id or not client_secret:
        print("❌ Error: Google OAuth2 credentials not configured!")
        print("\nPlease set up your Google Cloud Console credentials first:")
        print("1. Go to: https://console.cloud.google.com/")
        print("2. Create a new project or select existing one")
        print("3. Enable Google Drive API and Google Docs API")
        print("4. Create OAuth2 credentials (Desktop application)")
        print("5. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to your .env file")
        print("\nThen run this script again.")
        sys.exit(1)
    
    print("✅ Found Google OAuth2 credentials in .env file")
    
    # Create OAuth2 flow
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"]
        }
    }
    
    print("\n🌐 Starting OAuth2 flow...")
    print("This will open your browser for Google login.")
    
    try:
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        creds = flow.run_local_server(port=0)
        
        print("✅ Authentication successful!")
        
        # Test the credentials by making a simple API call
        print("🧪 Testing Google Drive API access...")
        service = build('drive', 'v3', credentials=creds)
        
        # Get user info
        about = service.about().get(fields="user").execute()
        user_email = about.get('user', {}).get('emailAddress', 'Unknown')
        
        print(f"✅ Successfully authenticated as: {user_email}")
        
        # Save refresh token to .env file
        refresh_token = creds.refresh_token
        if refresh_token:
            update_env_file(refresh_token)
            print("✅ Refresh token saved to .env file")
        else:
            print("❌ Warning: No refresh token received. You may need to revoke existing permissions and try again.")
            return
        
        print("\n🎉 Setup complete!")
        print("Your application can now access Google Drive documents privately.")
        print("You won't need to authenticate again unless you revoke access.")
        
    except Exception as e:
        print(f"❌ Error during authentication: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure your Google Cloud Console credentials are correct")
        print("2. Ensure the OAuth2 consent screen is configured")
        print("3. Check that Google Drive API and Google Docs API are enabled")
        sys.exit(1)

if __name__ == "__main__":
    main()