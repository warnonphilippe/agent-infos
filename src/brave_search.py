import asyncio
import os
import json
from typing import Any, List, Dict

# Imports MCP et LangChain
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# --- CONFIGURATION ---
# 1. Clé OpenAI pour le "Cerveau"
os.environ["OPENAI_API_KEY"] = "sk-..." 

# 2. Clé Brave pour le "Serveur MCP" (L'outil de recherche)
# Dans un vrai cas, mettez cela dans vos variables d'environnement système
os.environ["BRAVE_API_KEY"] = "BSA-..." 

async def run_news_agent():
    print("🗞️ Démarrage de l'Agent Journaliste MCP...")

    # On lance le serveur "brave-search".
    # Ce serveur expose des outils pour chercher sur le web (news, local, etc.)
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-brave-search"],
        env={
            "BRAVE_API_KEY": os.environ["BRAVE_API_KEY"],
            "PATH": os.environ["PATH"] # Important pour que npx fonctionne
        }
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            
            # 1. Initialisation
            await session.initialize()
            
            # 2. Découverte des outils (Dynamique !)
            # L'agent va découvrir qu'il possède maintenant des outils comme "brave_web_search"
            tools_list = await session.list_tools()
            print(f"\n✅ Serveur connecté. Outils disponibles : {[t.name for t in tools_list.tools]}")

            # 3. Préparation pour le LLM (Traduction en format OpenAI)
            llm_tools = []
            for tool in tools_list.tools:
                llm_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema
                    }
                })

            # 4. Le "Cerveau" (LLM)
            llm = ChatOpenAI(model="gpt-4o")
            llm_with_tools = llm.bind(functions=llm_tools)

            # --- LA REQUÊTE UTILISATEUR ---
            user_query = "Quelles sont les dernières actualités importantes sur l'IA aujourd'hui ?"
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
                    name=tool_name,
                    arguments=tool_args
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

            else:
                print("Le LLM a répondu sans utiliser d'outils (ce qui est bizarre pour des news récentes).")

if __name__ == "__main__":
    asyncio.run(run_news_agent())