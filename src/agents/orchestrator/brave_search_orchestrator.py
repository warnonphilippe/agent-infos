"""Agent and orchestration for the news search workflow."""

import logging
from typing import Dict, Optional, Any
from langgraph.graph import StateGraph, END

from src.agents.nodes import (
    brave_search_node,
    extract_search_results_node,
    summarize_results_node,
    format_results_node,
)
from src.agents.types import NewsState

logger = logging.getLogger(__name__)


class BraveSearchOrchestrator:
    """Builds and runs the LangGraph workflow for news processing."""

    def __init__(self) -> None:
        self.compiled_graph = None

    @staticmethod
    async def _build_graph():
        from langgraph.prebuilt import ToolNode, tools_condition
        from src.agents.mcp_tools import MCPBraveSearchTools

        workflow = StateGraph(NewsState)

        # Initialize tools
        factory = MCPBraveSearchTools()
        tools = await factory.get_tools_as_langchain()
        tool_node = ToolNode(tools)

        # Add nodes
        workflow.add_node("agent", brave_search_node)
        workflow.add_node("tools", tool_node)
        workflow.add_node("extract", extract_search_results_node)
        workflow.add_node("format", format_results_node)
        workflow.add_node("summarize", summarize_results_node)

        # Define edges/routing
        workflow.set_entry_point("agent")

        # Conditional edge: agent -> tools OR agent -> extract
        workflow.add_conditional_edges(
            "agent", tools_condition, {"tools": "tools", "__end__": "extract"}
        )

        # Loop back from tools to agent
        workflow.add_edge("tools", "agent")

        # Continue flow after extraction
        workflow.add_edge("extract", "format")
        workflow.add_edge("format", "summarize")
        workflow.add_edge("summarize", END)

        return workflow.compile()

    async def run(self, user_query: str) -> Dict[str, Any]:
        """Execute the workflow and return the result."""
        initial_state: NewsState = {
            "query": user_query,
            "messages": [],  # Initialize empty message list
            "search_results": None,
            "formatted_results": None,
            "structured_results": None,
            "final_summary": None,
        }

        # Since _build_graph is now async, we need to handle it
        if not hasattr(self, "compiled_graph") or self.compiled_graph is None:
            self.compiled_graph = await self._build_graph()

        final_state = await self.compiled_graph.ainvoke(initial_state)
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
