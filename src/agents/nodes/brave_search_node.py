"""Node for performing Brave Search via MCP."""

import os
import logging
from typing import Dict, Any

from langchain_core.messages import HumanMessage
from langchain_openai import AzureChatOpenAI

from src.config.settings import settings
from src.agents.types import NewsState

# MCP Imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult

logger = logging.getLogger(__name__)


async def brave_search_node(state: NewsState) -> Dict[str, Any]:
    """
    Node 1: Search
    Connects to MCP, discovers tools, decides which tool to use, executes it.
    Returns the search results as text.
    """
    user_query = state["query"]
    print("🗞️ Démarrage de l'Agent Journaliste MCP pour la recherche...")

    brave_key = settings.brave_api_key
    if not brave_key:
        logger.warning("No Brave API key configured (BRAVE_API_KEY)")

    # MCP Server Parameters
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-brave-search"],
        env={
            **os.environ.copy(),
            "BRAVE_API_KEY": brave_key or "",
        },
    )

    search_results = ""

    # MCP Context Lifecycle
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 1. Initialize
            await session.initialize()

            # 2. List Tools
            tools_list = await session.list_tools()
            print(
                f"\n✅ Serveur connecté. Outils disponibles : {[t.name for t in tools_list.tools]}"
            )

            # 3. LLM Setup
            llm_tools = []
            for tool in tools_list.tools:
                llm_tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.input_schema,
                        },
                    }
                )

            llm = AzureChatOpenAI(
                azure_deployment=settings.azure_openai_chat_deployment,
                api_version=settings.azure_openai_api_version,
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
            )
            llm_with_tools = llm.bind(tools=llm_tools)

            print(f"\n👤 Question : {user_query}")
            messages = [HumanMessage(content=user_query)]

            # 4. Invoke LLM
            ai_msg = llm_with_tools.invoke(messages)

            # 5. Handle Response
            if ai_msg.tool_calls:
                tool_call = ai_msg.tool_calls[0]
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                print(f"🤖 Le LLM veut utiliser : {tool_name}")
                print(f"   Paramètres : {tool_args}")
                print("⏳ Interrogation du serveur MCP (Recherche Brave)...")

                result: CallToolResult = await session.call_tool(
                    name=tool_name, arguments=tool_args
                )

                if result.content:
                    search_results = result.content[0].text
                    print(f"✅ Résultats reçus ({len(search_results)} caractères).")
                else:
                    search_results = "Aucun contenu retourné par l'outil."
                    print("⚠️ Aucun contenu retourné.")
            else:
                print("Le LLM a répondu sans utiliser d'outils.")
                search_results = ai_msg.content

    return {"search_results": search_results}
