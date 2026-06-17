"""
MCP Server providing tools for Ollama via vault-assistant.
Provides: date/time, web search, file access, etc.
"""

from datetime import datetime
import json
from typing import Any


class MCPToolProvider:
    """Provides MCP-compatible tools for LLM use."""

    def __init__(self):
        self.tools = {
            "get_current_date": {"description": "Get the current date and time", "parameters": {}},
            "web_search": {
                "description": "Search the web for information",
                "parameters": {"query": {"type": "string", "description": "Search query"}},
            },
            "list_vault_files": {
                "description": "List files in the vault",
                "parameters": {"path": {"type": "string", "description": "Vault path (optional)"}},
            },
        }

    def get_available_tools(self) -> dict:
        """Return available tools."""
        return self.tools

    def execute_tool(self, tool_name: str, parameters: dict) -> str:
        """Execute a tool and return result."""
        if tool_name == "get_current_date":
            return self._get_current_date()
        elif tool_name == "web_search":
            return self._web_search(parameters.get("query", ""))
        elif tool_name == "list_vault_files":
            return self._list_vault_files(parameters.get("path", ""))
        else:
            return f"Unknown tool: {tool_name}"

    def _get_current_date(self) -> str:
        """Get current date and time."""
        now = datetime.now()
        return f"Current date and time: {now.strftime('%Y-%m-%d %H:%M:%S')}"

    def _web_search(self, query: str) -> str:
        """Perform web search (placeholder - would use DuckDuckGo/Brave)."""
        try:
            import requests

            # Using DuckDuckGo (no API key needed)
            response = requests.get("https://duckduckgo.com/", params={"q": query, "format": "json"}, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if "results" in data:
                    results = data["results"][:3]
                    return json.dumps(
                        {"query": query, "results": [{"title": r.get("title"), "url": r.get("url")} for r in results]}
                    )
        except Exception as e:
            pass
        return f"Web search not available for query: {query}"

    def _list_vault_files(self, path: str = "") -> str:
        """List files in the vault."""
        try:
            from pathlib import Path
            from config import Config

            vault_path = Config.VAULT_PATH
            if path:
                vault_path = vault_path / path

            if vault_path.exists():
                files = [f.name for f in vault_path.glob("*.md")][:10]
                return json.dumps({"path": str(vault_path), "files": files, "count": len(files)})
        except Exception as e:
            pass
        return "Could not list vault files"


# Global provider instance
mcp_provider = MCPToolProvider()


def get_tools():
    """Get available tools."""
    return mcp_provider.get_available_tools()


def execute_tool(tool_name: str, parameters: dict):
    """Execute a tool."""
    return mcp_provider.execute_tool(tool_name, parameters)
