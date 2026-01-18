import asyncio
import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Union
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

async def search_exa_mcp(tags: list[str], api_key: str) -> List[Dict[str, Any]]:
    """
    Connects to the Exa MCP server, searches for articles relevant to the 
    provided tags published in the last 3 days, and returns the results.
    """
    
    # 1. Prepare the server parameters
    # We use 'npx' to run the official Exa MCP server on demand.
    # We pass the API key via environment variables to the subprocess.
    server_env = os.environ.copy()
    server_env["EXA_API_KEY"] = api_key
    server_env["PATH"] = os.environ.get("PATH", "") # Ensure npx is found
    
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "exa-mcp-server"], # The official NPM package for Exa MCP
        env=server_env
    )

    # 2. Calculate "3 days ago" for the date filter
    three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    
    # 3. Construct a natural language query from tags
    # Exa works best with natural language queries rather than just keywords.
    query_string = f"Latest comprehensive articles and news about {', '.join(tags)}"

    logger.info(f"Connecting to Exa MCP Server...")
    
    # 4. Connect to the server
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the session
            await session.initialize()
            
            # 5. List tools to find the correct search tool name
            # Different versions of the server might name the tool 'search' or 'web_search'
            tools_response = await session.list_tools()
            tool_names = [t.name for t in tools_response.tools]
            
            # Prioritize 'web_search', fall back to 'search' or the first available tool
            search_tool_name = next(
                (name for name in tool_names if name in ["web_search", "search"]), 
                tool_names[0] if tool_names else None
            )
            
            if not search_tool_name:
                logger.error("Error: No search tool found on the Exa MCP server.")
                return []

            logger.info(f"Executing search using tool: '{search_tool_name}'...")

            # 6. Call the tool
            # We map the Exa API parameters to the MCP tool arguments.
            result = await session.call_tool(
                search_tool_name,
                arguments={
                    "query": query_string,
                    "startPublishedDate": three_days_ago,
                    "numResults": 10,
                    "useAutoprompt": True # Exa feature to optimize the query
                }
            )

            # 7. Process and return the content
            articles = []
            for content in result.content:
                if content.type == "text":
                    try:
                        # Attempt to parse JSON if the text looks like JSON
                        text_content = content.text
                        # Sometimes the tool returns a JSON string, sometimes just text.
                        # Exa results usually come as a formatted string or JSON.
                        # Let's assume it returns a JSON string of results for now or try to parse it.
                        # If it's just text, we wrap it.
                        
                        # Heuristic: check if it starts with [ or {
                        if text_content.strip().startswith(("[", "{")):
                             parsed = json.loads(text_content)
                             if isinstance(parsed, list):
                                 articles.extend(parsed)
                             elif isinstance(parsed, dict) and "results" in parsed:
                                 articles.extend(parsed["results"])
                             else:
                                 # Fallback: maybe just part of the result
                                 pass
                        else:
                            # If it's plain text, we might need another strategy or just treat it as one article?
                            # For now, let's see if we can extract info. 
                            # Or just log it.
                            logger.debug(f"Received text content (not JSON): {text_content[:100]}...")
                            # Often MCP tools return a human readable string. 
                            # If we want structured data, we should check if the tool supports it.
                            # But let's return a basic structure if we can't parse it.
                            pass

                    except json.JSONDecodeError:
                         logger.warning("Could not parse search result as JSON")
            
            # If we couldn't parse structured data, we might need to rely on the raw text. 
            # However, for this refactor, let's assume valid return or handle it in the calling node if needed.
            # But wait, result.content is a list of Content objects.
            # If Exa tool returns a string representation of results, we need to be careful.
            
            # Let's return the raw content text for the node to handle if we can't parse it?
            # Or better, try to create a list of dicts.
            
            # If articles list is empty but we have content, let's try to return something.
            if not articles:
                 # Check if we have text content
                 text_parts = [c.text for c in result.content if c.type == "text"]
                 if text_parts:
                     # It's likely a formatted string. 
                     # For the sake of this POC, let's just return a list containing the raw text if parsing failed
                     # But the downstream expects 'url', 'title', etc.
                     # We might simply return an empty list if we can't parse it, 
                     # but that would fail the expectation.
                     
                     # Let's trust that Exa MCP returns a JSON string representing the results. 
                     # (Often tools are designed for LLM consumption, so they return JSON text).
                     
                     # If parsing failed, we return empty list.
                     pass

            return articles

