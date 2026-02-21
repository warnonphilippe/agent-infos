"""Shared types for LangGraph workflows."""

from typing import Dict, List, TypedDict, Optional, Annotated
from langgraph.graph.message import add_messages
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
    messages: Annotated[List, add_messages]
    search_results: Optional[str]
    formatted_results: Optional[str]
    structured_results: Optional[List[Dict]]
    final_summary: Optional[str]
