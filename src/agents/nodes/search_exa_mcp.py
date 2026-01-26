import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

async def search_exa_mcp(tags: List[str], api_key: str) -> List[Dict[str, Any]]:
    """
    Connects to the remote Exa MCP server via mcp-remote bridge and searches for articles.
    """
    
    # 2. Calculate "3 days ago" for the date filter
    three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    
    # 3. Construct a natural language query from tags
    # We join tags to make a coherent query.
    if tags:
        query_string = f"Latest comprehensive articles and news about {', '.join(tags)}"
    else:
        query_string = "Latest comprehensive articles and news about AI"

    logger.info(f"Connecting to remote Exa MCP Server using query: {query_string}")
    
    try:
        # Configure the connection using npx and mcp-remote
        server_params = StdioServerParameters(
            command="npx",
            args=[
                "-y", 
                "mcp-remote", 
                # According to docs/logs, using mcp-remote with exa endpoint
                f"https://mcp.exa.ai/mcp" 
            ],
            env={
                **os.environ.copy(),
                # mcp-remote might need the key in header via args or env?
                # Actually, mcp-remote supports custom headers via specific args or implicit forwarding if implemented.
                # But typically Exa MCP expects headers.
                # If mcp-remote doesn't support headers easily, we might need to rely on the URL param method the user tried:
                # https://mcp.exa.ai/mcp?exaApiKey=...
                # Let's try to stick to the valid one.
            }
        )
        
        # NOTE: The user's code had `https://mcp.exa.ai/mcp?exaApiKey={api_key}`.
        # This is likely the correct way to auth with mcp-remote if headers aren't forwarded.
        # Let's preserve that logic but clean up the surrounding code.
        
        server_params.args[2] = f"https://mcp.exa.ai/mcp?exaApiKey={api_key}"

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # List available tools to be safe and debug
                tools = await session.list_tools()
                tool_names = [t.name for t in tools.tools]
                logger.info(f"Connected to Exa! Found tools: {tool_names}")
                
                # Determine too name
                search_tool = "web_search_exa" if "web_search_exa" in tool_names else "search"
                if search_tool not in tool_names:
                    # Fallback to first one
                    search_tool = tool_names[0] if tool_names else None
                
                if not search_tool:
                     return []

                # Run a search
                result = await session.call_tool(
                    search_tool,
                    arguments={
                        "query": query_string,
                        "numResults": 10,
                        "useAutoprompt": True,
                        # "startPublishedDate": three_days_ago # Optional, can add back if needed
                    }
                )

                articles = []
                for content in result.content:
                    if content.type == "text":
                        text_content = content.text
                        
                        # PARSING LOGIC:
                        # The user provided example output which is a flat STRING with multiple articles separated by newlines?
                        # Or it looks like a dump of text.
                        # Actually, looking at the user's provided logs:
                        # [TextContent(type='text', text='Title: ...\nAuthor: ...\nPublished Date: ...\nURL: ...\nText: ...')]
                        # This is unstructured text, NOT JSON.
                        # We need to parse this custom text format.
                        
                        # Simple parser for "Title: ... \n URL: ..." blocks
                        
                        raw_text = text_content
                        # Split by "Title: " to find potential articles
                        # This is heuristic but necessary given the output format.
                        
                        # We can also check if it IS json first.
                        if raw_text.strip().startswith("[") or raw_text.strip().startswith("{"):
                             try:
                                 parsed = json.loads(raw_text)
                                 if isinstance(parsed, list):
                                     articles.extend(parsed)
                                     continue
                                 elif isinstance(parsed, dict) and "results" in parsed:
                                     articles.extend(parsed["results"])
                                     continue
                             except:
                                 pass
                        
                        # Fallback: Parse the custom text format
                        # Format seems to be:
                        # Title: <title>
                        # Author: <author>
                        # Published Date: <date>
                        # URL: <url>
                        # Text: <text>
                        
                        # We can split by "Title: "
                        segments = raw_text.split("\nTitle: ")
                        if raw_text.startswith("Title: "):
                            segments[0] = segments[0].replace("Title: ", "")
                        else:
                            # If the first segment doesn't start with Title, it might be preamble.
                            pass
                            
                        for segment in segments:
                            if not segment.strip(): continue
                            
                            # Re-add "Title: " prefix for uniformity if we split by it? 
                            # Actually, split removes the delimiter.
                            # Let's map lines.
                            
                            lines = segment.split("\n")
                            article_data = {}
                            current_key = "title" # Default start? 
                            
                            # Heuristic parsing
                            # The split removed "Title: ", so the first line is the title (or remainder of it)
                            article_data["title"] = lines[0].strip()
                            
                            body_lines = []
                            capture_text = False
                            
                            for line in lines[1:]:
                                if line.startswith("Author: "):
                                    article_data["author"] = line.replace("Author: ", "").strip()
                                    capture_text = False
                                elif line.startswith("Published Date: "):
                                    article_data["publishedDate"] = line.replace("Published Date: ", "").strip()
                                    capture_text = False
                                elif line.startswith("URL: "):
                                    article_data["url"] = line.replace("URL: ", "").strip()
                                    capture_text = False
                                elif line.startswith("Text: "):
                                    capture_text = True
                                    content_start = line.replace("Text: ", "").strip()
                                    if content_start:
                                        body_lines.append(content_start)
                                else:
                                    # Continuation of previous field or Text
                                    if capture_text:
                                        body_lines.append(line)
                            
                            article_data["text"] = "\n".join(body_lines)
                            
                            # Basic validation
                            if article_data.get("url"):
                                articles.append(article_data)

                return articles

    except Exception as e:
        logger.error(f"Failed to connect or search with Exa MCP server: {e}")
        return []
