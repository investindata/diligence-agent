"""
MCP server configuration for CrewAI.
"""

import os
from crewai_tools import MCPServerAdapter
from crewai_tools.adapters.mcp_adapter import StdioServerParameters


def get_slack_tools():
    """Get Slack MCP tools if configured, empty list otherwise."""
    if not (os.getenv('SLACK_BOT_TOKEN') and os.getenv('SLACK_TEAM_ID')):
        return []
    
    slack_config = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-slack"],
        env={
            "SLACK_BOT_TOKEN": os.getenv('SLACK_BOT_TOKEN'),
            "SLACK_TEAM_ID": os.getenv('SLACK_TEAM_ID'),
            "SLACK_CHANNEL_IDS": os.getenv('SLACK_CHANNEL_IDS', ''),
        }
    )
    
    try:
        # MCPServerAdapter expects a single server parameter, not a list
        adapter = MCPServerAdapter(slack_config)
        return list(adapter.tools)
    except Exception as e:
        print(f"Warning: Slack MCP not available: {e}")
        return []