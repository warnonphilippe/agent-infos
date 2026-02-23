"""Settings and configuration management."""

import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    azure_openai_endpoint: str = Field(..., description="Azure OpenAI endpoint URL")
    azure_openai_api_key: str = Field(..., description="Azure OpenAI API key")
    azure_openai_chat_deployment: str = Field(
        default="gpt-5-chat", description="Azure OpenAI chat deployment name"
    )
    azure_openai_api_version: str = Field(
        default="2025-01-01-preview", description="Azure OpenAI API version"
    )
    langchain_api_key: str = Field(..., description="LangChain API key")
    exa_api_key: Optional[str] = Field(
        default=None, description="Exa API key for MCP search"
    )
    brave_api_key: Optional[str] = Field(
        default=None, description="Brave API key for details"
    )
    mailtrap_api_token: Optional[str] = Field(
        default=None, description="Mailtrap API token"
    )
    mailtrap_account_id: Optional[int] = Field(
        default=None, description="Mailtrap account ID"
    )
    mailtrap_from_email: str = Field(
        default="test@example.com", description="Default sender for email summary"
    )
    mailtrap_to_email: str = Field(
        default="test@example.com", description="Default recipient for email summary"
    )

    # MCP servers configuration - can be set via environment variable as comma-separated list
    mcp_servers: List[str] = Field(
        default_factory=list, description="List of MCP server URLs"
    )

    # Path to tags file
    tags_file: Path = Field(
        default=Path(__file__).parent.parent / "assets" / "tags.txt",
        description="Path to the tags file",
    )

    # Request timeout for MCP servers (in seconds)
    mcp_timeout: int = Field(
        default=30, description="Timeout for MCP server requests in seconds"
    )

    @field_validator("mcp_servers", mode="before")
    @classmethod
    def parse_mcp_servers(cls, v: any) -> List[str]:
        """Parse MCP servers from comma-separated string or list."""
        if v is None:
            return []
        if isinstance(v, list):
            return [str(url).strip() for url in v if url]
        if isinstance(v, str):
            return [url.strip() for url in v.split(",") if url.strip()]
        return []

    @property
    def mcp_servers_list(self) -> List[str]:
        """Get MCP servers as a list."""
        if isinstance(self.mcp_servers, list):
            return self.mcp_servers
        if isinstance(self.mcp_servers, str):
            return [url.strip() for url in self.mcp_servers.split(",") if url.strip()]
        return []

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
