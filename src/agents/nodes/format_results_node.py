"""Node for formatting search results."""

import json
import logging
from typing import Dict, Any

from src.agents.types import NewsState

logger = logging.getLogger(__name__)


async def format_results_node(state: NewsState) -> Dict[str, Any]:
    """
    Node: Format Results
    Parses the raw search results and formats them into a structured string (Markdown).
    Expected structure: Title, Content, Link per item.
    """
    raw_results = state.get("search_results", "")
    formatted_text = ""

    if not raw_results:
        return {"formatted_results": "Aucun résultat à formater."}

    items = []
    try:
        data = json.loads(raw_results)
        items = []

        # Attempt to locate the results list in typical Brave Search JSON responses
        if isinstance(data, dict):
            if (
                "web" in data
                and isinstance(data["web"], dict)
                and "results" in data["web"]
            ):
                items = data["web"]["results"]
            elif "results" in data and isinstance(data["results"], list):
                items = data["results"]
            else:
                # If valid JSON dict but unknown structure, treat as single item or fallback
                items = []
        elif isinstance(data, list):
            items = data

        # Format each item
        for item in items:
            if not isinstance(item, dict):
                continue

            title = item.get("title", "Sans titre")
            # Description can be in various fields
            content = (
                item.get("description")
                or item.get("snippet")
                or item.get("extract_html")
                or "Pas de contenu disponible"
            )
            link = item.get("url") or item.get("link") or "#"

            formatted_text += f"### {title}\n**Source**: {link}\n\n{content}\n\n---\n\n"

        if not formatted_text and raw_results:
            # If JSON parse worked but no items found or formatting produced empty string
            # Fallback to crude display if raw_results wasn't empty
            formatted_text = f"Résultats non structurés :\n{raw_results[:500]}..."

    except json.JSONDecodeError:
        # If not JSON, return as is or minimal format
        logger.warning("Could not parse search results as JSON")
        formatted_text = f"Résultats bruts (non JSON) :\n\n{raw_results}"
    except Exception as e:
        logger.error(f"Error formatting results: {e}")
        formatted_text = f"Erreur de formatage : {str(e)}"

    return {"formatted_results": formatted_text, "structured_results": items}
