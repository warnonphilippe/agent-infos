"""Agent and orchestration for the article search workflow."""
import logging
from typing import Dict, Optional
from langgraph.graph import StateGraph, END

from src.agents.nodes import (
    load_tags_node,
    build_queries_node,
    fetch_articles_node,
    filter_articles_node,
    rank_articles_node,
    select_top_10_node,
    generate_summary_node,
    format_response_node,
)
from src.agents.types import AgentState

logger = logging.getLogger(__name__)


class ArticlesOrchestrator:
    """Builds and runs the LangGraph workflow for article processing."""

    def __init__(self) -> None:
        self.graph = self._build_graph()

    @staticmethod
    def _build_graph():
        workflow = StateGraph(AgentState)

        workflow.add_node("load_tags", load_tags_node)
        workflow.add_node("build_queries", build_queries_node)
        workflow.add_node("fetch_articles", fetch_articles_node)
        workflow.add_node("filter_articles", filter_articles_node)
        workflow.add_node("rank_articles", rank_articles_node)
        workflow.add_node("select_top_10", select_top_10_node)
        workflow.add_node("generate_summary", generate_summary_node)
        workflow.add_node("format_response", format_response_node)

        workflow.set_entry_point("load_tags")
        workflow.add_edge("load_tags", "build_queries")
        workflow.add_edge("build_queries", "fetch_articles")
        workflow.add_edge("fetch_articles", "filter_articles")
        workflow.add_edge("filter_articles", "rank_articles")
        workflow.add_edge("rank_articles", "select_top_10")
        workflow.add_edge("select_top_10", "generate_summary")
        workflow.add_edge("generate_summary", "format_response")
        workflow.add_edge("format_response", END)

        return workflow.compile()

    async def run(self, initial_state: Optional[AgentState] = None) -> Dict:
        """Execute the workflow and return the result payload."""
        logger.info("Starting articles orchestrator workflow")
        state: AgentState = initial_state or {
            "tags": [],
            "queries": [],
            "articles": [],
            "filtered_articles": [],
            "ranked_articles": [],
            "top_articles": [],
            "summary": "",
            "result": {},
        }

        final_state = await self.graph.ainvoke(state)
        result = final_state.get("result", {})
        logger.info("Articles orchestrator workflow completed")
        return result


class ArticleSearchAgent:
    """Agent facade that delegates to the LangGraph orchestrator."""

    def __init__(self) -> None:
        self.orchestrator = ArticlesOrchestrator()

    async def run(self) -> Dict:
        """Run the orchestrated workflow and return the result."""
        try:
            return await self.orchestrator.run()
        except Exception as exc:  # noqa: BLE001
            logger.error("Error in article search workflow: %s", exc)
            raise
