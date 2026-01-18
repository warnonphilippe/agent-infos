"""Node to rank articles by relevance."""
import logging
from src.agents.article_processor import rank_articles
from src.agents.types import AgentState

logger = logging.getLogger(__name__)


def rank_articles_node(state: AgentState) -> AgentState:
    """Rank filtered articles for relevance."""
    logger.info("Ranking articles by relevance")
    filtered_articles = state.get("filtered_articles", [])

    ranked = rank_articles(filtered_articles)
    logger.info("Ranked %d articles", len(ranked))
    return {**state, "ranked_articles": ranked}
