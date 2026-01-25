import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from mcp import ClientSession
from mcp.client.sse import sse_client

logger = logging.getLogger(__name__)

async def search_exa_mcp(tags: List[str], api_key: str) -> List[Dict[str, Any]]:
    """
    Connects to the remote Exa MCP server, searches for articles relevant to the 
    provided tags published in the last 3 days, and returns the results.
    """
    
    # 1. Server Connection Details
    # Use the official Exa hosted MCP server
    exa_mcp_url = "https://mcp.exa.ai/mcp"
    
    # Pass the API key in headers (standard Exa/MCP auth)
    headers = {
        "x-api-key": api_key,
        "User-Agent": "agent-infos-poc/1.0"
    }
    
    # 2. Calculate "3 days ago" for the date filter
    three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    
    # 3. Construct a natural language query from tags
    query_string = f"Latest comprehensive articles and news about {', '.join(tags)}"

    logger.info(f"Connecting to remote Exa MCP Server at {exa_mcp_url}...")
    
    try:
        # 4. Connect to the server via SSE
        async with sse_client(exa_mcp_url, headers=headers) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()
                
                # 5. List available tools
                tools_response = await session.list_tools()
                tool_names = [t.name for t in tools_response.tools]
                logger.debug(f"Available tools: {tool_names}")
                
                # Prioritize 'web_search' or 'search', fall back to the first available
                search_tool_name = next(
                    (name for name in tool_names if name in ["web_search", "search"]), 
                    tool_names[0] if tool_names else None
                )
                
                if not search_tool_name:
                    logger.error("Error: No search tool found on the Exa MCP server.")
                    return []

                logger.info(f"Executing search using tool: '{search_tool_name}'...")

                # 6. Call the search tool
                result = await session.call_tool(
                    search_tool_name,
                    arguments={
                        "query": query_string,
                        "startPublishedDate": three_days_ago,
                        "numResults": 10,
                        "useAutoprompt": True
                    }
                )

                # 7. Process and return the content
                articles = []
                for content in result.content:
                    if content.type == "text":
                        try:
                            text_content = content.text
                            # Attempt to parse JSON if it looks like it
                            if text_content.strip().startswith(("[", "{")):
                                 parsed = json.loads(text_content)
                                 if isinstance(parsed, list):
                                     articles.extend(parsed)
                                 elif isinstance(parsed, dict) and "results" in parsed:
                                     articles.extend(parsed["results"])
                                 else:
                                     pass
                            else:
                                # Not JSON, might be plain text result
                                logger.debug(f"Received text content (not JSON): {text_content[:100]}...")
                                pass

                        except json.JSONDecodeError:
                             logger.warning("Could not parse search result as JSON")
                
                return articles

    except Exception as e:
        logger.error(f"Failed to connect or search with Exa MCP server: {e}")
        return []
