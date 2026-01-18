"""Node to build search queries from tags."""
import logging
from typing import List
from src.agents.types import AgentState

logger = logging.getLogger(__name__)


def build_queries_node(state: AgentState) -> AgentState:
    """Create search queries based on tags and defaults."""
    tags = [tag for tag in state.get("tags", []) if tag]
    queries: List[str] = []

    if tags:
        queries.extend([f"best technical articles about {tag}" for tag in tags])
        combined = ", ".join(tags)
        queries.append(f"best technical articles about {combined}")
    else:
        queries.append("best technical articles about ai, python, java, spring, langchain")

    logger.info("Built %d search queries", len(queries))
    return {**state, "queries": queries}
