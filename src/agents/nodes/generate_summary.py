"""Node to generate a summary via LLM."""
import json
import logging
from src.agents.types import AgentState
from src.config.llm_config import get_llm, get_summary_prompt

logger = logging.getLogger(__name__)


async def generate_summary_node(state: AgentState) -> AgentState:
    """Generate a summary with the LLM and attach reasons."""
    logger.info("Generating summary with LLM")
    top_articles = state.get("top_articles", [])
    tags = state.get("tags", [])

    if not top_articles:
        empty_result = {
            "summary": "Aucun article trouvé.",
            "top_articles": []
        }
        return {**state, "summary": empty_result["summary"], "result": empty_result}

    try:
        llm = get_llm()
        prompt = get_summary_prompt()

        articles_text = "\n".join(
            [
                f"- {article.title} ({article.url}) - Published: {article.published_at or 'Unknown'}"
                for article in top_articles
            ]
        )

        messages = prompt.format_messages(tags=", ".join(tags), articles=articles_text)
        response = await llm.ainvoke(messages)

        summary_text = response.content
        try:
            if "```json" in summary_text:
                json_start = summary_text.find("```json") + 7
                json_end = summary_text.find("```", json_start)
                summary_text = summary_text[json_start:json_end].strip()
            elif "```" in summary_text:
                json_start = summary_text.find("```") + 3
                json_end = summary_text.find("```", json_start)
                summary_text = summary_text[json_start:json_end].strip()

            result = json.loads(summary_text)
            summary = result.get("summary", summary_text)
            top_articles_data = result.get("top_articles", [])

            final_articles = []
            for idx, article in enumerate(top_articles[:10]):
                article_dict = {
                    "title": article.title,
                    "url": article.url,
                    "published_at": article.published_at.isoformat() if article.published_at else None,
                    "source": article.source,
                    "tags": article.tags,
                }

                if idx < len(top_articles_data):
                    llm_article = top_articles_data[idx]
                    if llm_article.get("title") == article.title or llm_article.get("url") == article.url:
                        article_dict["relevance_reason"] = llm_article.get(
                            "relevance_reason",
                            "Article intéressant",
                        )
                    else:
                        article_dict["relevance_reason"] = "Article pertinent selon les critères de sélection"
                else:
                    article_dict["relevance_reason"] = "Article pertinent selon les critères de sélection"

                final_articles.append(article_dict)

            result_dict = {"summary": summary, "top_articles": final_articles}
            return {**state, "summary": summary, "result": result_dict}
        except json.JSONDecodeError:
            logger.warning("Could not parse LLM response as JSON, using raw response")
            fallback_result = {
                "summary": summary_text,
                "top_articles": [
                    {
                        "title": article.title,
                        "url": article.url,
                        "published_at": article.published_at.isoformat() if article.published_at else None,
                        "source": article.source,
                        "tags": article.tags,
                        "relevance_reason": "Article pertinent selon les critères de sélection",
                    }
                    for article in top_articles[:10]
                ],
            }
            return {**state, "summary": summary_text, "result": fallback_result}
    except Exception as exc:  # noqa: BLE001
        logger.error("Error generating summary: %s", exc)
        fallback_result = {
            "summary": f"Résumé non disponible. {len(top_articles)} articles trouvés.",
            "top_articles": [
                {
                    "title": article.title,
                    "url": article.url,
                    "published_at": article.published_at.isoformat() if article.published_at else None,
                    "source": article.source,
                    "tags": article.tags,
                    "relevance_reason": "Article pertinent selon les critères de sélection",
                }
                for article in top_articles[:10]
            ],
        }
        return {**state, "summary": fallback_result["summary"], "result": fallback_result}
