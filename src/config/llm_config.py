"""LLM configuration and initialization."""
import logging
from pathlib import Path

from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from src.config.settings import settings

logger = logging.getLogger(__name__)

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


def load_prompt(filename: str) -> str:
    """Load prompt content from assets directory."""
    try:
        # Prompt files should be in src/assets
        # __file__ is src/config/llm_config.py
        # parent = src/config, parent.parent = src
        path = Path(__file__).parent.parent / "assets" / filename
        return path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Failed to load prompt file {filename}: {e}")
        # Fallback empty string or raise? 
        # For now raise so we know config is broken
        raise

def get_summary_prompt() -> ChatPromptTemplate:
    """
    Get the prompt template for generating article summaries.
    
    Returns:
        ChatPromptTemplate: Prompt template for summarization
    """
    system_prompt = load_prompt("summary_system_prompt.md")
    user_prompt = load_prompt("summary_user_prompt.md")
    
    return ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", user_prompt)
    ])
