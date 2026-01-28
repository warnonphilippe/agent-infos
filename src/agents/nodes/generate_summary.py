"""Node to generate a summary via LLM."""
import logging
from typing import List, Optional
from pydantic import BaseModel, Field

from src.agents.types import AgentState
from src.config.llm_config import get_llm, get_summary_prompt

logger = logging.getLogger(__name__)


# Pydantic models for structured output
class ArticleReview(BaseModel):
    """Review of a specific article."""
    title: str = Field(..., description="Title of the article")
    url: str = Field(..., description="URL of the article")
    relevance_reason: str = Field(..., description="Why this article is relevant to the user query")

class SummaryResult(BaseModel):
    """Structure for the final summary output."""
    summary: str = Field(..., description="Comprehensive summary of the articles")
    top_articles: List[ArticleReview] = Field(..., description="List of the most relevant articles with reasons")


async def generate_summary_node(state: AgentState) -> AgentState:
    """Generate a summary with the LLM using structured output."""
    logger.info("Generating summary with LLM (Structured)")
    
    articles = state.get("articles", [])
    tags = state.get("tags", [])

    if not articles:
        empty_result = {
            "summary": "Aucun article trouvé pour ces critères.",
            "top_articles": []
        }
        return {**state, "summary": empty_result["summary"], "result": empty_result}

    try:
        # Take up to 15 articles to avoid context overflow, although we asked for 10
        display_articles = articles[:15]
        
        llm = get_llm()
        structured_llm = llm.with_structured_output(SummaryResult, method="function_calling")
        
        prompt = get_summary_prompt()

        articles_text = "\n".join(
            [
                f"- {article.get('title')} ({article.get('url')}) - Published: {article.get('published_at') or 'Unknown'}"
                for article in display_articles
            ]
        )

        messages = prompt.format_messages(tags=", ".join(tags), articles=articles_text)
        
        # Execute LLM with structured output enforcement
        result: SummaryResult = await structured_llm.ainvoke(messages)

        # Map back to the expected dictionary format for the state
        final_articles = []
        
        # We need to map the LLM's 'top_articles' back to our original article data 
        # to preserve fields like source, tags, published_at that the LLM might not return perfectly.
        # We'll create a lookup map by URL.
        article_map = {a.get("url"): a for a in display_articles}
        
        for reviewed_article in result.top_articles:
            original = article_map.get(reviewed_article.url)
            if original:
                # Handle cases where published_at might be object or string or None
                pub_at = original.get("published_at")
                if hasattr(pub_at, "isoformat"):
                    pub_str = pub_at.isoformat()
                else:
                    pub_str = str(pub_at) if pub_at else None

                final_articles.append({
                    "title": original.get("title"),
                    "url": original.get("url"),
                    "published_at": pub_str,
                    "source": original.get("source"),
                    "tags": original.get("tags", []),
                    "relevance_reason": reviewed_article.relevance_reason,
                    "content": original.get("content"),
                })
        
        result_dict = {
            "summary": result.summary, 
            "top_articles": final_articles
        }
        
        return {**state, "summary": result.summary, "result": result_dict}

    except Exception as exc:
        logger.error("Error generating summary with structured output: %s", exc)
        # Fallback to a simple message
        fallback_result = {
            "summary": f"Erreur lors de la génération du résumé. {len(articles)} articles identifiés.",
            "top_articles": [
                {
                    "title": a.get("title"),
                    "url": a.get("url"),
                    "published_at": str(a.get("published_at")) if a.get("published_at") else None,
                    "source": a.get("source"),
                    "tags": a.get("tags", []),
                    "relevance_reason": "Article trouvé (Fallback)"
                } for a in articles[:10]
            ]
        }
        return {**state, "summary": fallback_result["summary"], "result": fallback_result}
