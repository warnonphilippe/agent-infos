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
        return {"result": {"email_status": "skipped_no_summary"}}

    api_token = settings.mailtrap_api_token
    sender = settings.mailtrap_from_email
    recipient = settings.mailtrap_to_email

    if not api_token:
        logger.error("No Mailtrap API token configured (MAILTRAP_API_TOKEN)")
        return {"result": {"email_status": "failed_no_token"}}

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
                email_args = {
                    "to": [recipient],
                    "subject": "Résumé quotidien des articles IA",
                    "text": summary,  # Fallback text
                    "html": f"<h1>Résumé des Articles</h1><div>{summary}</div>",  # Basic HTML wrapping
                    "category": "Daily Summary",
                }

                print(f"📨 Envoi à {recipient}...")

                result: CallToolResult = await session.call_tool(
                    name=tool_to_use, arguments=email_args
                )

                if result.content:
                    content_texts = [c.text for c in result.content if c.type == "text"]
                    result_text = "\n".join(content_texts)
                    print(f"✅ Email envoyé : {result_text}")
                    return {"result": {"email_status": "sent", "details": result_text}}
                else:
                    print("⚠️ Email envoyé mais aucun retour.")
                    return {"result": {"email_status": "sent_no_details"}}

    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return {"result": {"email_status": "failed", "error": str(e)}}
