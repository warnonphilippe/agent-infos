"""Shared types for LangGraph workflows."""
from typing import Dict, List, TypedDict
from src.agents.nodes.article_processor import Article


class AgentState(TypedDict):
    """State for the LangGraph agent workflow."""
    tags: List[str]
    queries: List[str]
    articles: List[Dict]
    summary: str
    result: Dict
