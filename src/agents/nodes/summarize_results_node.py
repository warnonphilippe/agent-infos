"""Node for summarizing search results."""

import logging
from typing import Dict, Any

from langchain_core.messages import HumanMessage
from langchain_openai import AzureChatOpenAI

from src.config.settings import settings
from src.agents.types import NewsState

logger = logging.getLogger(__name__)


async def summarize_results_node(state: NewsState) -> Dict[str, Any]:
    """
    Node 2: Summarize
    Takes the search results and generates a clear summary.
    """
    search_results = state.get("search_results")
    user_query = state["query"]

    if not search_results:
        return {"final_summary": "Aucun résultat à résumer."}

    llm = AzureChatOpenAI(
        azure_deployment=settings.azure_openai_chat_deployment,
        api_version=settings.azure_openai_api_version,
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
    )

    prompt = (
        f"Voici les résultats de recherche pour la requête : '{user_query}'\n\n"
        f"Résultats :\n{search_results}\n\n"
        "Fais-moi une synthèse claire et journalistique. \n\n"
        "IMPORTANT : Pour chaque information importante, cite obligatoirement la source avec son URL (cliquable si possible en Markdown)."
    )
    msg = HumanMessage(content=prompt)

    response = await llm.ainvoke([msg])

    print("\n📰 --- FLASH INFO ---")
    print(response.content)
    print("---------------------")

    return {"final_summary": response.content}
