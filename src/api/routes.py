"""FastAPI routes for the MCP article summarizer."""
import logging
from fastapi import APIRouter, HTTPException
from typing import Dict

from src.agents.article_search_agent import ArticleSearchAgent

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/generate")
async def generate_summary() -> Dict:
    """
    Generate a summary and list of top 10 articles from MCP servers.
    
    This endpoint:
    1. Loads tags from assets/tags.txt
    2. Fetches articles from configured MCP servers (last 3 days)
    3. Filters articles by tags
    4. Ranks and selects top 10 articles
    5. Generates a summary using Azure OpenAI
    
    Returns:
        Dictionary containing:
        - summary: Global summary of main themes
        - top_articles: List of top 10 articles with relevance reasons
        
    Raises:
        HTTPException: If the agent workflow fails
    """
    try:
        logger.info("Received request to generate summary")
        agent = ArticleSearchAgent()
        result = await agent.run()
        
        if not result:
            raise HTTPException(
                status_code=500,
                detail="Agent workflow completed but returned no result"
            )
        
        logger.info("Summary generated successfully")
        return result
        
    except Exception as e:
        logger.error(f"Error generating summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error generating summary: {str(e)}"
        )


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.
    
    Returns:
        Status dictionary indicating the service is healthy
    """
    return {"status": "ok"}
