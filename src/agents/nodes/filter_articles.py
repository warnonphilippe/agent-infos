"""Node to filter articles by tags."""
import logging
from src.agents.nodes.article_processor import filter_articles_by_tags
from src.agents.types import AgentState

logger = logging.getLogger(__name__)


def filter_articles_node(state: AgentState) -> AgentState:
    """Filter articles using requested tags."""
    logger.info("Filtering articles by tags")
    articles = state.get("articles", [])
    tags = state.get("tags", [])

    filtered = filter_articles_by_tags(articles, tags)
    logger.info("Filtered to %d articles matching tags", len(filtered))
    return {**state, "filtered_articles": filtered}
