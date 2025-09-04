#!/usr/bin/env python3
"""
Test Slack MCP integration.
"""

import os
import sys
import pytest
sys.path.append('../src')

from diligence_agent.mcp_config import get_slack_tools


def test_slack_credentials_configured():
    """Test that Slack credentials are configured."""
    bot_token = os.getenv('SLACK_BOT_TOKEN')
    team_id = os.getenv('SLACK_TEAM_ID')
    
    if not bot_token or not team_id:
        pytest.skip("Slack credentials not configured")
    
    assert bot_token.startswith('xoxb-'), "Bot token should start with xoxb-"
    assert team_id.startswith('T'), "Team ID should start with T"


def test_slack_tools_available():
    """Test that Slack MCP tools can be loaded."""
    slack_tools = get_slack_tools()
    
    if not (os.getenv('SLACK_BOT_TOKEN') and os.getenv('SLACK_TEAM_ID')):
        assert slack_tools == [], "Should return empty list when not configured"
    else:
        assert isinstance(slack_tools, list), "Should return a list"
        # Tools may or may not be available depending on MCP server status


if __name__ == "__main__":
    # Quick manual test
    print("Testing Slack MCP integration...")
    
    bot_token = os.getenv('SLACK_BOT_TOKEN')
    team_id = os.getenv('SLACK_TEAM_ID')
    
    print(f"Bot Token configured: {'✅' if bot_token else '❌'}")
    print(f"Team ID configured: {'✅' if team_id else '❌'}")
    
    if bot_token and team_id:
        try:
            slack_tools = get_slack_tools()
            print(f"Slack tools loaded: {'✅' if slack_tools else '❌'}")
            print(f"Number of tools: {len(slack_tools)}")
            
            if slack_tools:
                print("\nAvailable Slack tools:")
                for i, tool in enumerate(slack_tools, 1):
                    print(f"  {i}. {getattr(tool, 'name', 'Unknown tool')}")
                    
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print("❌ Slack credentials not configured")