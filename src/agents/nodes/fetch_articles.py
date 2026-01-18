"""Node to fetch articles from MCP servers."""
import logging
from datetime import datetime, timedelta
from src.agents.search_exa_mcp import search_exa_mcp
from src.agents.types import AgentState
from src.config.settings import settings

logger = logging.getLogger(__name__)


async def fetch_articles_node(state: AgentState) -> AgentState:
    """Fetch articles using Exa MCP."""
    logger.info("Fetching articles via Exa MCP")
    tags = state.get("tags", [])
    
    exa_key = settings.exa_api_key
    if not exa_key:
        logger.warning("No Exa API key configured (EXA_API_KEY)")
        return {**state, "articles": []}

    try:
        raw_articles = await search_exa_mcp(tags, exa_key)
        
        # Normalize Exa results to Article structure
        normalized_articles = []
        for item in raw_articles:
            normalized_articles.append({
                "title": item.get("title", "Untitled"),
                "url": item.get("url", ""),
                "published_at": item.get("publishedDate"),
                "content": item.get("text") or item.get("summary") or "",
                "tags": [], # Exa doesn't return tags usually, filtering node will handle
                "source": "Exa MCP"
            })
            
        logger.info("Fetched %d articles from Exa", len(normalized_articles))
        return {**state, "articles": normalized_articles}
    except Exception as exc:  # noqa: BLE001
        logger.error("Error fetching articles from Exa: %s", exc)
        return {**state, "articles": []}
