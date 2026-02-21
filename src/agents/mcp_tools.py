import os
import asyncio
from typing import List, Any, Dict
from langchain_core.tools import tool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from src.config.settings import settings


class MCPBraveSearchTools:
    """Helper to convert MCP Brave Search tools to LangChain tools."""

    def __init__(self):
        self.server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-brave-search"],
            env={
                **os.environ.copy(),
                "BRAVE_API_KEY": settings.brave_api_key or "",
            },
        )
        self._session = None
        self._exit_stack = None

    async def get_tools_as_langchain(self):
        """
        Connects to MCP and returns tools wrapped for LangChain.
        NOTE: This implementation is tricky because MCP session is async context managed.
        For ToolNode, we often want pre-defined tools.
        """
        # For simplicity in this demo, we'll return a list of tools that
        # internally manage the MCP connection for each call.
        # A more performant way would be a persistent connection.

        @tool
        async def brave_web_search(query: str, count: int = 5) -> str:
            """Search the web using Brave Search."""
            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(
                        "brave_web_search", arguments={"query": query, "count": count}
                    )
                    if result.content:
                        return result.content[0].text
                    return "No results found."

        @tool
        async def brave_local_search(query: str, count: int = 5) -> str:
            """Search for local places using Brave Search."""
            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(
                        "brave_local_search", arguments={"query": query, "count": count}
                    )
                    if result.content:
                        return result.content[0].text
                    return "No results found."

        return [brave_web_search, brave_local_search]
