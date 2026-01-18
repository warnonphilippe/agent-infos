"""Shared types for LangGraph workflows."""
from typing import Dict, List, TypedDict
from src.agents.article_processor import Article


class AgentState(TypedDict):
    """State for the LangGraph agent workflow."""
    tags: List[str]
    queries: List[str]
    articles: List[Dict]
    filtered_articles: List[Article]
    ranked_articles: List[Article]
    top_articles: List[Article]
    summary: str
    result: Dict
