"""Node to select top N articles."""
import logging
from src.agents.article_processor import select_top_articles
from src.agents.types import AgentState

logger = logging.getLogger(__name__)


def select_top_10_node(state: AgentState) -> AgentState:
    """Select the top 10 ranked articles."""
    logger.info("Selecting top 10 articles")
    ranked_articles = state.get("ranked_articles", [])

    top_10 = select_top_articles(ranked_articles, top_n=10)
    logger.info("Selected %d top articles", len(top_10))
    return {**state, "top_articles": top_10}
