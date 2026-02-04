"""FastAPI routes for the MCP article summarizer."""

import logging
from fastapi import APIRouter, HTTPException
from typing import Dict

from src.agents.article_search_agent import ArticleSearchAgent
from src.brave_search import run_news_agent
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/articles")
async def generate_summary() -> Dict:
    """
    Generate a summary about best articles from MCP servers.

    This endpoint:
    1. Loads tags from assets/tags.txt
    2. Fetches articles from configured MCP servers (last 3 days)
    3. Generates a summary using Azure OpenAI

    Returns:
        Dictionary containing:
        - summary: Global summary of main themes

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
                detail="Agent workflow completed but returned no result",
            )

        logger.info("Summary generated successfully")
        return result

    except Exception as e:
        logger.error(f"Error generating summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error generating summary: {str(e)}"
        )


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.

    Returns:
        Status dictionary indicating the service is healthy
    """
    return {"status": "ok"}


class NewsRequest(BaseModel):
    query: str


@router.post("/news")
async def run_news(request: NewsRequest) -> Dict[str, str]:
    """
    Run the news agent with a user query.

    Args:
        request: NewsRequest containing the user query

    Returns:
        Dictionary containing the agent's response
    """
    try:
        logger.info(f"Received news request: {request.query}")
        result = await run_news_agent(request.query)
        return {"response": result}
    except Exception as e:
        logger.error(f"Error running news agent: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error running news agent: {str(e)}"
        )
