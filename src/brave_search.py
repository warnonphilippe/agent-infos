import asyncio
import json
import os
import logging

from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.config.settings import settings

# Imports MCP et LangChain
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult

logger = logging.getLogger(__name__)


# --- CONFIGURATION ---
# 1. Clé OpenAI pour le "Cerveau"
openai_api_key = settings.azure_openai_api_key

# 2. Clé Brave pour le "Serveur MCP" (L'outil de recherche)
brave_api_key = settings.brave_api_key


async def run_news_agent(user_query: str) -> str:
    print("🗞️ Démarrage de l'Agent Journaliste MCP...")

    brave_key = settings.brave_api_key
    if not brave_key:
        logger.warning("No Brave API key configured (BRAVE_API_KEY)")

    # On lance le serveur "brave-search".
    # Ce serveur expose des outils pour chercher sur le web (news, local, etc.)
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-brave-search"],
        env={
            **os.environ.copy(),
            "BRAVE_API_KEY": settings.brave_api_key,
        },
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:

            # 1. Initialisation
            await session.initialize()

            # 2. Découverte des outils (Dynamique !)
            # L'agent va découvrir qu'il possède maintenant des outils comme "brave_web_search"
            tools_list = await session.list_tools()
            print(
                f"\n✅ Serveur connecté. Outils disponibles : {[t.name for t in tools_list.tools]}"
            )

            # 3. Préparation pour le LLM (Traduction en format OpenAI)
            llm_tools = []
            for tool in tools_list.tools:
                llm_tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.inputSchema,
                        },
                    }
                )

            # 4. Le "Cerveau" (LLM)
            llm = ChatOpenAI(model="gpt-4o")
            llm_with_tools = llm.bind(functions=llm_tools)

            # --- LA REQUÊTE UTILISATEUR ---
            print(f"\n👤 Question : {user_query}")

            messages = [HumanMessage(content=user_query)]

            # Premier appel au LLM
            ai_msg = llm_with_tools.invoke(messages)
            messages.append(ai_msg)

            # 5. Boucle d'exécution
            if ai_msg.additional_kwargs.get("function_call"):
                fc = ai_msg.additional_kwargs["function_call"]
                tool_name = fc["name"]
                tool_args = json.loads(fc["arguments"])

                print(f"🤖 Le LLM veut utiliser : {tool_name}")
                print(f"   Paramètres : {tool_args}")

                # APPEL AU SERVEUR MCP
                # L'agent exécute la recherche de news
                print("⏳ Interrogation du serveur MCP (Recherche Brave)...")
                result: CallToolResult = await session.call_tool(
                    name=tool_name, arguments=tool_args
                )

                # Récupération des résultats (souvent du JSON ou du texte brut)
                search_results = result.content[0].text

                print(f"✅ Résultats reçus ({len(search_results)} caractères).")

                # 6. Synthèse finale
                # On redonne les news brutes au LLM pour qu'il fasse un résumé propre
                feed_back_msg = f"Voici les résultats bruts de la recherche : {search_results}. Fais-moi une synthèse claire."
                messages.append(HumanMessage(content=feed_back_msg))

                final_response = llm.invoke(messages)

                print("\n📰 --- FLASH INFO ---")
                print(final_response.content)
                print("---------------------")

                return final_response.content

            else:
                print("Le LLM a répondu sans utiliser d'outils.")
                return ai_msg.content


# if __name__ == "__main__":
#    asyncio.run(run_news_agent())
