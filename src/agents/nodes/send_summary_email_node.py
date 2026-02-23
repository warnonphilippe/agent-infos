"""Node for sending the formatted summary via Mailtrap."""

import os
import logging
from typing import Dict, Any

from src.config.settings import settings
from src.agents.types import AgentState

# MCP Imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult

logger = logging.getLogger(__name__)


async def send_summary_email_node(state: AgentState) -> Dict[str, Any]:
    """
    Node: Send Summary Email
    Takes the generated summary from the state and sends it via Mailtrap.
    """
    print("📧 Envoi du résumé par email...")

    summary = state.get("summary", "")
    if not summary:
        logger.warning("No summary available to send.")
        return {
            "result": {**state.get("result", {}), "email_status": "skipped_no_summary"}
        }

    # Extract top articles from result to append to email
    result_data = state.get("result", {})
    top_articles = result_data.get("top_articles", [])

    articles_html = ""
    articles_text = ""
    if top_articles:
        articles_html += "<h2>Top Articles</h2><ul>"
        articles_text += "\n\nTop Articles:\n"
        for idx, article in enumerate(top_articles, 1):
            title = article.get("title", "Sans titre")
            url = article.get("url", "#")
            reason = article.get("relevance_reason", "")

            articles_html += f"<li><strong><a href='{url}'>{title}</a></strong><br><i>{reason}</i></li><br>"
            articles_text += f"{idx}. {title} ({url})\n   {reason}\n\n"
        articles_html += "</ul>"

    # We update the original result dictionary rather than overwriting it
    def return_with_status(status_updates: dict) -> dict:
        result_cpy = dict(state.get("result", {}))
        result_cpy.update(status_updates)
        return {"result": result_cpy}

    api_token = settings.mailtrap_api_token
    sender = settings.mailtrap_from_email
    recipient = settings.mailtrap_to_email

    if not api_token:
        logger.error("No Mailtrap API token configured (MAILTRAP_API_TOKEN)")
        return return_with_status({"email_status": "failed_no_token"})

    # Prepare environment variables for the MCP server
    env_vars = os.environ.copy()
    env_vars["MAILTRAP_API_TOKEN"] = api_token
    env_vars["DEFAULT_FROM_EMAIL"] = sender

    # MCP Server Parameters
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "mcp-mailtrap"],
        env=env_vars,
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Check for available tools to prefer sandbox if available and configured
                tools_list = await session.list_tools()
                tool_names = [t.name for t in tools_list.tools]

                # Determine which tool to use
                if "send-email" in tool_names:
                    tool_to_use = "send-email"
                else:
                    raise Exception("No email tool available")

                print(f"🛠️ Utilisation de l'outil : {tool_to_use}")

                # Prepare email content
                text_content = summary + articles_text
                # Convert the newlines in summary (if any) to <br> to prevent losing newlines in HTML but since the original was just <div>{summary}</div> maybe it's fine.
                html_content = f"<h1>Résumé des Articles</h1><div style='white-space: pre-wrap;'>{summary}</div>{articles_html}"

                email_args = {
                    "to": [recipient],
                    "subject": "Résumé quotidien des articles IA",
                    "text": text_content,  # Fallback text
                    "html": html_content,  # Basic HTML wrapping
                    "category": "Daily Summary",
                }

                print(f"📨 Envoi à {recipient}...")

                result_tool: CallToolResult = await session.call_tool(
                    name=tool_to_use, arguments=email_args
                )

                if result_tool.content:
                    content_texts = [
                        c.text for c in result_tool.content if c.type == "text"
                    ]
                    result_text = "\n".join(content_texts)
                    print(f"✅ Email envoyé : {result_text}")
                    return return_with_status(
                        {"email_status": "sent", "details": result_text}
                    )
                else:
                    print("⚠️ Email envoyé mais aucun retour.")
                    return return_with_status({"email_status": "sent_no_details"})

    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return return_with_status({"email_status": "failed", "error": str(e)})
