"""Node to format the final response payload."""
import logging
from src.agents.types import AgentState

logger = logging.getLogger(__name__)


def format_response_node(state: AgentState) -> AgentState:
    """Ensure result is present in state for output."""
    logger.info("Formatting final response")
    result = state.get("result", {})
    return {**state, "result": result}
