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
            **os.environ
        }
    )
    
    try:
        # MCPServerAdapter expects a single server parameter, not a list
        adapter = MCPServerAdapter(slack_config)
        return list(adapter.tools)
    except Exception as e:
        print(f"Warning: Slack MCP not available: {e}")
        return []


def get_playwright_tools():
    """Get Playwright MCP tools for web scraping and browser automation."""
    # Check if we want to enable headless mode (default: False to show browser)
    headless = os.getenv('PLAYWRIGHT_HEADLESS', 'false').lower() == 'true'
    
    # Build args list
    args = [
        "@playwright/mcp@latest",
        "--browser", "chrome",  # Use Chrome browser
        "--timeout-navigation", "30000",  # 30 second navigation timeout
        "--timeout-action", "10000",      # 10 second action timeout
    ]
    
    # Add headless flag if enabled
    if headless:
        args.append("--headless")
    
    # Use persistent profile for LinkedIn authentication
    user_data_dir = os.path.expanduser("~/.cache/playwright-profile")
    args.extend(["--user-data-dir", user_data_dir])
    
    playwright_config = StdioServerParameters(
        command="npx",
        args=args,
        env={
            "NODE_ENV": "production",
            "LINKEDIN_EMAIL": os.getenv('LINKEDIN_EMAIL', ''),
            "LINKEDIN_PASSWORD": os.getenv('LINKEDIN_PASSWORD', ''),
            **os.environ
        }
    )
    
    try:
        adapter = MCPServerAdapter(playwright_config, connect_timeout=60)
        return list(adapter.tools)
    except Exception as e:
        print(f"Warning: Playwright MCP not available: {e}")
        return []


def get_playwright_tools_with_auth():
    """Get Playwright MCP tools with LinkedIn authentication support."""
    # Alternative approach using storage state for authentication
    headless = os.getenv('PLAYWRIGHT_HEADLESS', 'false').lower() == 'true'
    
    args = [
        "@playwright/mcp@latest",
        "--browser", "chrome",
        "--timeout-navigation", "30000",
        "--timeout-action", "10000",
    ]
    
    if headless:
        args.append("--headless")
    
    # Use storage state file for persistent login
    storage_state_path = os.path.expanduser("~/.cache/linkedin-auth.json")
    if os.path.exists(storage_state_path):
        args.extend(["--storage-state", storage_state_path])
    
    playwright_config = StdioServerParameters(
        command="npx",
        args=args,
        env={
            "NODE_ENV": "production",
            **os.environ
        }
    )
    
    try:
        adapter = MCPServerAdapter(playwright_config, connect_timeout=60)
        return list(adapter.tools)
    except Exception as e:
        print(f"Warning: Playwright MCP not available: {e}")
        return []