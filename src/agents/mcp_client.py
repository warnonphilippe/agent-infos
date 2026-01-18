"""MCP (Model Context Protocol) client for communicating with MCP servers."""
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import httpx
from dateutil import parser as date_parser

from src.config.settings import settings

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for communicating with MCP servers using JSON-RPC 2.0 protocol."""
    
    def __init__(self, server_url: str, timeout: Optional[int] = None):
        """
        Initialize MCP client.
        
        Args:
            server_url: Base URL of the MCP server
            timeout: Request timeout in seconds (defaults to settings.mcp_timeout)
        """
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout or settings.mcp_timeout
        self._request_id = 0
    
    def _get_next_request_id(self) -> int:
        """Get next JSON-RPC request ID."""
        self._request_id += 1
        return self._request_id
    
    async def _call_jsonrpc(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a JSON-RPC 2.0 call to the MCP server.
        
        Args:
            method: JSON-RPC method name
            params: Method parameters
            
        Returns:
            Response from the server
            
        Raises:
            httpx.HTTPError: If the HTTP request fails
            ValueError: If the response is invalid
        """
        request_id = self._get_next_request_id()
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params:
            payload["params"] = params
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.server_url}/jsonrpc",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                result = response.json()
                
                if "error" in result:
                    error = result["error"]
                    raise ValueError(
                        f"MCP server error: {error.get('message', 'Unknown error')} "
                        f"(code: {error.get('code', 'unknown')})"
                    )
                
                return result.get("result", {})
        except httpx.TimeoutException:
            logger.error(f"Timeout connecting to MCP server: {self.server_url}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"HTTP error connecting to MCP server {self.server_url}: {e}")
            raise
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List available tools on the MCP server.
        
        Returns:
            List of available tools with their descriptions
        """
        try:
            result = await self._call_jsonrpc("tools/list")
            return result.get("tools", [])
        except Exception as e:
            logger.warning(f"Could not list tools from {self.server_url}: {e}")
            return []
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Call a tool on the MCP server.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        return await self._call_jsonrpc(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments or {}
            }
        )
    
    async def fetch_articles(
        self,
        since_date: datetime,
        tags: Optional[List[str]] = None,
        query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch articles from the MCP server published since the given date.
        
        This method tries different approaches to fetch articles:
        1. Try to call a semantic 'search' tool if available
        1. Try to call a dedicated 'fetch_articles' tool if available
        2. Try to call 'search_articles' tool
        3. Try to call 'list_resources' and filter by date
        
        Args:
            since_date: Only fetch articles published after this date
            tags: Optional list of tags to filter by
            
        Returns:
            List of articles with flexible format
        """
        articles = []
        
        # Try different methods to fetch articles
        tools = await self.list_tools()
        tool_names = [tool.get("name", "") for tool in tools]

        # Preferred: semantic search tool
        if query and "search" in tool_names:
            try:
                result = await self.call_tool(
                    "search",
                    {
                        "query": query,
                        "start_published_date": since_date.isoformat(),
                    },
                )
                articles = self._normalize_articles(result.get("results", []) or result.get("articles", []))
            except Exception as exc:  # noqa: BLE001
                logger.warning("search tool failed: %s", exc)
        
        # Method 1: Try fetch_articles tool
        if not articles and "fetch_articles" in tool_names:
            try:
                result = await self.call_tool(
                    "fetch_articles",
                    {
                        "since": since_date.isoformat(),
                        "tags": tags or []
                    }
                )
                articles = self._normalize_articles(result.get("articles", []))
            except Exception as e:
                logger.warning(f"fetch_articles tool failed: {e}")
        
        # Method 2: Try search_articles tool
        elif not articles and "search_articles" in tool_names:
            try:
                result = await self.call_tool(
                    "search_articles",
                    {
                        "query": " ".join(tags or []),
                        "since": since_date.isoformat()
                    }
                )
                articles = self._normalize_articles(result.get("articles", []))
            except Exception as e:
                logger.warning(f"search_articles tool failed: {e}")
        
        # Method 3: Try list_resources
        elif "list_resources" in tool_names:
            try:
                result = await self._call_jsonrpc("resources/list")
                resources = result.get("resources", [])
                # Filter resources by date if they have metadata
                for resource in resources:
                    if resource.get("uri", "").startswith("article://"):
                        articles.append({
                            "title": resource.get("name", "Untitled"),
                            "url": resource.get("uri", ""),
                            "source": self.server_url
                        })
            except Exception as e:
                logger.warning(f"list_resources failed: {e}")
        
        # Filter articles by date
        filtered_articles = []
        for article in articles:
            published_at = self._parse_date(article.get("published_at") or article.get("date"))
            if published_at and published_at >= since_date:
                filtered_articles.append(article)
        
        return filtered_articles
    
    def _normalize_articles(self, raw_articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize articles from different MCP servers to a common format.
        
        Args:
            raw_articles: Raw articles from MCP server
            
        Returns:
            Normalized articles
        """
        normalized = []
        for article in raw_articles:
            normalized.append({
                "title": article.get("title") or article.get("name") or "Untitled",
                "url": article.get("url") or article.get("uri") or article.get("link") or "",
                "published_at": article.get("published_at") or article.get("date") or article.get("pubDate"),
                "content": article.get("content") or article.get("summary") or article.get("description") or "",
                "tags": article.get("tags") or article.get("categories") or [],
                "source": article.get("source") or self.server_url
            })
        return normalized
    
    def _parse_date(self, date_str: Any) -> Optional[datetime]:
        """
        Parse a date string to datetime object.
        
        Args:
            date_str: Date string or datetime object
            
        Returns:
            Parsed datetime or None if parsing fails
        """
        if date_str is None:
            return None
        if isinstance(date_str, datetime):
            return date_str
        try:
            return date_parser.parse(str(date_str))
        except (ValueError, TypeError):
            logger.warning(f"Could not parse date: {date_str}")
            return None


async def fetch_articles_from_all_servers(
    server_urls: List[str],
    since_date: datetime,
    tags: Optional[List[str]] = None,
    queries: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch articles from multiple MCP servers in parallel.
    
    Args:
        server_urls: List of MCP server URLs
        since_date: Only fetch articles published after this date
        tags: Optional list of tags to filter by
        
    Returns:
        Combined list of articles from all servers
    """
    import asyncio
    
    tasks = []
    for url in server_urls:
        client = MCPClient(url)
        if queries:
            for query in queries:
                tasks.append(client.fetch_articles(since_date, tags, query=query))
        else:
            tasks.append(client.fetch_articles(since_date, tags))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    all_articles = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Error fetching from {server_urls[i]}: {result}")
            continue
        all_articles.extend(result)
    
    # Deduplicate articles by URL
    seen_urls = set()
    unique_articles = []
    for article in all_articles:
        url = article.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_articles.append(article)
    
    return unique_articles
