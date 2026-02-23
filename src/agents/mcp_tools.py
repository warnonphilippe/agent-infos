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


class MCPMailtrapTools:
    """Helper to convert MCP Mailtrap tools to LangChain tools."""

    def __init__(self):
        env_vars = os.environ.copy()
        env_vars["MAILTRAP_API_TOKEN"] = settings.mailtrap_api_token or ""
        env_vars["DEFAULT_FROM_EMAIL"] = settings.mailtrap_from_email or ""

        self.server_params = StdioServerParameters(
            command="npx",
            args=["-y", "mcp-mailtrap"],
            env=env_vars,
        )

    async def get_tools_as_langchain(self):
        """
        Connects to MCP and returns tools wrapped for LangChain.
        """

        @tool
        async def send_email(
            to: List[str], subject: str, text: str, html: str = "", category: str = ""
        ) -> str:
            """Send an email using Mailtrap."""
            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    # We assume send-email is available as per the mailtrap MCP
                    arguments = {
                        "to": to,
                        "subject": subject,
                        "text": text,
                    }
                    if html:
                        arguments["html"] = html
                    if category:
                        arguments["category"] = category

                    result = await session.call_tool("send-email", arguments=arguments)

                    if result.content:
                        content_texts = [
                            c.text for c in result.content if c.type == "text"
                        ]
                        return "\n".join(content_texts)
                    return "Email sent, but no output returned."

        return [send_email]


class MCPExaSearchTools:
    """Helper to convert MCP Exa Search tools to LangChain tools."""

    def __init__(self):
        api_key = settings.exa_api_key or ""
        self.server_params = StdioServerParameters(
            command="npx",
            args=["-y", "mcp-remote", f"https://mcp.exa.ai/mcp?exaApiKey={api_key}"],
            env=os.environ.copy(),
        )

    async def get_tools_as_langchain(self):
        """
        Connects to MCP and returns tools wrapped for LangChain.
        """

        @tool
        async def exa_web_search(
            query: str, num_results: int = 5, use_autoprompt: bool = True
        ) -> str:
            """Search the web using Exa Search."""
            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    tools = await session.list_tools()
                    tool_names = [t.name for t in tools.tools]

                    search_tool = (
                        "web_search_exa" if "web_search_exa" in tool_names else "search"
                    )
                    if search_tool not in tool_names:
                        search_tool = tool_names[0] if tool_names else None

                    if not search_tool:
                        return "No search tool found."

                    result = await session.call_tool(
                        search_tool,
                        arguments={
                            "query": query,
                            "numResults": num_results,
                            "useAutoprompt": use_autoprompt,
                        },
                    )

                    if result.content:
                        content_texts = [
                            c.text for c in result.content if c.type == "text"
                        ]
                        return "\n\n".join(content_texts)
                    return "No results found."

        return [exa_web_search]
