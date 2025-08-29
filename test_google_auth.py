#!/usr/bin/env python3
"""
Test script to verify Google OAuth2 authentication is working
"""

import sys
import os
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from diligence_agent.tools.google_doc_processor import GoogleDocProcessor

def test_google_auth():
    print("🧪 Testing Google OAuth2 Authentication")
    print("=" * 50)
    
    # Test URL
    test_url = "https://docs.google.com/spreadsheets/d/11nh2sUQSOsq1f2KJDgAx_zfeYyMxHUPUYY7N3NigpXg/edit?usp=sharing"
    
    print(f"📄 Testing document: {test_url}")
    print()
    
    try:
        # Create the processor
        processor = GoogleDocProcessor()
        
        print("🔍 Attempting to access document...")
        content = processor._run(test_url)
        
        print("✅ SUCCESS! Document accessed successfully")
        print(f"📊 Content length: {len(content)} characters")
        print()
        print("📝 First 500 characters of content:")
        print("-" * 40)
        print(content[:500])
        if len(content) > 500:
            print("...")
        print("-" * 40)
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_google_auth()
    
    if success:
        print("\n🎉 Google OAuth2 authentication is working!")
        print("Your application can now access private Google documents.")
    else:
        print("\n💡 Troubleshooting tips:")
        print("1. Make sure the document is shared with your Google account")
        print("2. Check that GOOGLE_REFRESH_TOKEN is in your .env file") 
        print("3. Verify the document URL is correct")
        
    sys.exit(0 if success else 1)