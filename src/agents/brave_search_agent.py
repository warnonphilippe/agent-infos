"""Agent and orchestration for the news search workflow."""

import logging
from typing import Dict, Optional, Any
from langgraph.graph import StateGraph, END

from src.agents.nodes import (
    brave_search_node,
    summarize_results_node,
    format_results_node,
)
from src.agents.types import NewsState

logger = logging.getLogger(__name__)


class BraveSearchOrchestrator:
    """Builds and runs the LangGraph workflow for news processing."""

    def __init__(self) -> None:
        self.graph = self._build_graph()

    @staticmethod
    def _build_graph():
        workflow = StateGraph(NewsState)

        # Add nodes
        workflow.add_node("search", brave_search_node)
        workflow.add_node("format", format_results_node)
        workflow.add_node("summarize", summarize_results_node)

        # Define edges
        workflow.set_entry_point("search")
        workflow.add_edge("search", "format")
        workflow.add_edge("format", "summarize")
        workflow.add_edge("summarize", END)

        return workflow.compile()

    async def run(self, user_query: str) -> Dict[str, Any]:
        """Execute the workflow and return the result."""
        initial_state: NewsState = {
            "query": user_query,
            "search_results": None,
            "formatted_results": None,
            "structured_results": None,
            "final_summary": None,
        }

        final_state = await self.graph.ainvoke(initial_state)
        return {
            "summary": final_state.get(
                "final_summary", "Erreur: Pas de résumé généré."
            ),
            "details": final_state.get("formatted_results", "Aucun résultat trouvé."),
            "structured_results": final_state.get("structured_results", []),
        }


class BraveSearchAgent:
    """Agent facade that delegates to the LangGraph orchestrator."""

    def __init__(self) -> None:
        self.orchestrator = BraveSearchOrchestrator()

    async def run(self, user_query: str) -> Dict[str, Any]:
        """Run the orchestrated workflow and return the result."""
        try:
            return await self.orchestrator.run(user_query)
        except Exception as exc:  # noqa: BLE001
            logger.error("Error in news search workflow: %s", exc)
            raise


# Backward wrapper for API compatibility
async def run_news_agent(user_query: str) -> Dict[str, Any]:
    """
    Executes the news agent workflow.
    """
    agent = BraveSearchAgent()
    return await agent.run(user_query)
