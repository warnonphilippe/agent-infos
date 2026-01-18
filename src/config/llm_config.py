"""LLM configuration and initialization."""
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from src.config.settings import settings


def get_llm() -> AzureChatOpenAI:
    """
    Create and return an Azure OpenAI chat model instance.
    
    Returns:
        AzureChatOpenAI: Configured Azure OpenAI chat model
    """
    return AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        azure_deployment=settings.azure_openai_chat_deployment,
        api_version=settings.azure_openai_api_version,
        api_key=settings.azure_openai_api_key,
        temperature=0.7,
        model_name=settings.azure_openai_chat_deployment,
    )


def get_summary_prompt() -> ChatPromptTemplate:
    """
    Get the prompt template for generating article summaries.
    
    Returns:
        ChatPromptTemplate: Prompt template for summarization
    """
    return ChatPromptTemplate.from_messages([
        ("system", """Tu es un assistant expert qui analyse des articles techniques et scientifiques.
        
Ton rôle est de:
1. Générer un résumé global des thèmes principaux abordés dans les articles
2. Identifier les 10 articles les plus intéressants et pertinents
3. Expliquer pourquoi chaque article est intéressant en relation avec les sujets recherchés

Sois concis mais informatif dans tes réponses."""),
        ("human", """Voici une liste d'articles récents filtrés selon les tags suivants: {tags}

Articles:
{articles}

Génère:
1. Un résumé global des thèmes principaux (2-3 paragraphes)
2. Une liste des 10 articles les plus intéressants avec pour chacun:
   - Le titre
   - L'URL
   - Une explication courte (1-2 phrases) de pourquoi cet article est intéressant

Format ta réponse en JSON avec cette structure:
{{
  "summary": "résumé global...",
  "top_articles": [
    {{
      "title": "titre",
      "url": "url",
      "relevance_reason": "pourquoi intéressant"
    }}
  ]
}}""")
    ])
