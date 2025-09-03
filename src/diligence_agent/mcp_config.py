"""
MCP server configuration for CrewAI.
"""

import os
from crewai_tools import MCPServerAdapter


def get_slack_tools():
    """Get Slack MCP tools if configured, empty list otherwise."""
    if not (os.getenv('SLACK_BOT_TOKEN') and os.getenv('SLACK_TEAM_ID')):
        return []
    
    slack_config = {
        "name": "slack",
        "transport": {"type": "stdio"},
        "args": ["npx", "-y", "@modelcontextprotocol/server-slack"],
        "env": {
            "SLACK_BOT_TOKEN": os.getenv('SLACK_BOT_TOKEN'),
            "SLACK_TEAM_ID": os.getenv('SLACK_TEAM_ID'),
            "SLACK_CHANNEL_IDS": os.getenv('SLACK_CHANNEL_IDS', ''),
        }
    }
    
    try:
        adapter = MCPServerAdapter([slack_config])
        return list(adapter.get_tools())
    except Exception as e:
        print(f"Warning: Slack MCP not available: {e}")
        return []