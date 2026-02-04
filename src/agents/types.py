"""Shared types for LangGraph workflows."""

from typing import Dict, List, TypedDict, Optional
from src.agents.nodes.article_processor import Article


class AgentState(TypedDict):
    """State for the LangGraph agent workflow."""

    tags: List[str]
    queries: List[str]
    articles: List[Dict]
    summary: str
    result: Dict


class NewsState(TypedDict):
    """State for the news agent workflow."""

    query: str
    search_results: Optional[str]
    final_summary: Optional[str]
