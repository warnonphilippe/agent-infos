"""Node to load tags from the tags file."""
import logging
from src.agents.nodes.article_processor import load_tags_from_file
from src.agents.types import AgentState
from src.config.settings import settings

logger = logging.getLogger(__name__)


def load_tags_node(state: AgentState) -> AgentState:
    """Load tags from disk and update state."""
    logger.info("Loading tags from file")
    tags = load_tags_from_file(str(settings.tags_file))
    logger.info("Loaded %d tags: %s", len(tags), tags)
    return {**state, "tags": tags}
