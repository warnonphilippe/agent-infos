"""Node for starting the Brave Search agent."""

import json
import logging
from typing import Dict, Any, List
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage

from src.config.settings import settings
from src.agents.types import NewsState

logger = logging.getLogger(__name__)


async def brave_search_node(state: NewsState) -> Dict[str, Any]:
    """
    Agent Node: Logic for deciding whether to use search tools.
    """
    user_query = state["query"]
    messages = state.get("messages", [])

    # Initialize messages if empty
    if not messages:
        messages = [HumanMessage(content=user_query)]
        print(f"🗞️ Analyse de la requête : {user_query}")
    else:
        print("🤖 Réflexion de l'agent suite aux résultats...")

    llm = AzureChatOpenAI(
        azure_deployment=settings.azure_openai_chat_deployment,
        api_version=settings.azure_openai_api_version,
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
    )

    # Important: The tools must be bound externally or here
    # Since we want ToolNode to work, we must bind the same tools
    from src.agents.mcp_tools import MCPBraveSearchTools

    factory = MCPBraveSearchTools()
    tools = await factory.get_tools_as_langchain()

    llm_with_tools = llm.bind_tools(tools)

    ai_msg = await llm_with_tools.ainvoke(messages)

    # We return the AI message to be added to the 'messages' list by the reducer
    return {"messages": [ai_msg]}


async def extract_search_results_node(state: NewsState) -> Dict[str, Any]:
    """
    Post-tool node to extract the search results from tool messages.
    Preserves JSON structure to ensure URLs and metadata are not lost.
    """
    messages = state.get("messages", [])
    all_results = []

    print(f"🔍 Extraction des résultats à partir de {len(messages)} messages...")

    # Collect all tool responses
    for msg in messages:
        # Check for ToolMessage (usually msg.type == 'tool')
        msg_type = getattr(msg, "type", "")

        if msg_type == "tool":
            content = getattr(msg, "content", "")
            print(f"🛠️  Trouvé un résultat d'outil ({len(str(content))} chars)")
            try:
                # If it's JSON, parse it to extract structured data
                if isinstance(content, str):
                    data = json.loads(content)
                else:
                    data = content

                if isinstance(data, list):
                    all_results.extend(data)
                elif isinstance(data, dict):
                    # Handle various Brave Search JSON structures
                    if (
                        "web" in data
                        and isinstance(data["web"], dict)
                        and "results" in data["web"]
                    ):
                        all_results.extend(data["web"]["results"])
                    elif "results" in data and isinstance(data["results"], list):
                        all_results.extend(data["results"])
                    else:
                        all_results.append(data)
                else:
                    all_results.append({"content": content, "type": "raw_json"})
            except (json.JSONDecodeError, TypeError):
                all_results.append({"content": content, "type": "text"})

    # If no tool results, check if the LLM gave a direct answer
    if not all_results and messages:
        last_msg = messages[-1]
        msg_type = getattr(last_msg, "type", "")
        if msg_type == "ai" and not getattr(last_msg, "tool_calls", None):
            print("🤖 Pas d'outil utilisé, récupération de la réponse directe du LLM.")
            all_results.append(
                {
                    "title": "Réponse directe de l'agent",
                    "description": getattr(last_msg, "content", ""),
                    "url": "N/A",
                }
            )

    if all_results:
        print(f"✅ Total de {len(all_results)} items extraits.")
        # Ensure we always return a valid JSON string for search_results
        return {
            "search_results": json.dumps({"results": all_results}),
            "structured_results": all_results,
        }

    print("⚠️ Aucun résultat trouvé pendant l'extraction.")
    return {"search_results": "", "structured_results": []}
