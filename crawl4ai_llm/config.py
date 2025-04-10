"""
Configuration module for the product extraction system.
"""

import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables from .env file
load_dotenv()


class CrawlerConfig(BaseModel):
    """Crawler configuration settings."""

    cache_dir: str = Field(
        default=os.getenv("CACHE_DIR", "./cache"),
        description="Directory for storing cache files",
    )
    rate_limit: int = Field(
        default=int(os.getenv("CRAWL_RATE_LIMIT", "10")),
        description="Requests per minute",
    )
    headless: bool = Field(
        default=os.getenv("HEADLESS", "true").lower() == "true",
        description="Whether to run the browser in headless mode",
    )
    user_agent: str = Field(
        default=os.getenv("USER_AGENT", "Crawl4AI E-commerce Extractor/1.0"),
        description="User agent string to use for requests",
    )


class DatabaseConfig(BaseModel):
    """Database configuration settings."""

    host: str = Field(
        default=os.getenv("DB_HOST", "localhost"), description="Database host"
    )
    port: int = Field(
        default=int(os.getenv("DB_PORT", "5432")), description="Database port"
    )
    name: str = Field(
        default=os.getenv("DB_NAME", "product_extraction"), description="Database name"
    )
    user: str = Field(
        default=os.getenv("DB_USER", "postgres"), description="Database user"
    )
    password: str = Field(
        default=os.getenv("DB_PASSWORD", "postgres"), description="Database password"
    )

    def get_connection_string(self) -> str:
        """Get the database connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class LLMConfig(BaseModel):
    """LLM provider configuration settings."""

    provider: str = Field(
        default=os.getenv("DEFAULT_LLM_PROVIDER", "openai"),
        description="Default LLM provider (openai, anthropic, etc.)",
    )
    model: str = Field(
        default=os.getenv("DEFAULT_LLM_MODEL", "gpt-4"),
        description="Default LLM model to use",
    )
    temperature: float = Field(
        default=float(os.getenv("LLM_TEMPERATURE", "0.0")),
        description="Temperature for LLM generation",
    )
    max_tokens: int = Field(
        default=int(os.getenv("LLM_MAX_TOKENS", "2000")),
        description="Maximum tokens for LLM responses",
    )

    @property
    def api_key(self) -> Optional[str]:
        """Get the API key for the configured provider."""
        if self.provider == "openai":
            return os.getenv("OPENAI_API_KEY")
        elif self.provider == "anthropic":
            return os.getenv("ANTHROPIC_API_KEY")
        return None


class StorageConfig(BaseModel):
    """Storage configuration settings."""

    type: str = Field(
        default=os.getenv("STORAGE_TYPE", "json"),
        description="Storage type (json, etc.)",
    )
    path: str = Field(
        default=os.getenv("STORAGE_PATH", "./data/products"),
        description="Path for storage (directory for JSON storage)",
    )
    use_uuid: bool = Field(
        default=os.getenv("STORAGE_USE_UUID", "true").lower() == "true",
        description="Use UUIDs for product IDs (if False, uses SKU or URL hash)",
    )


class AppConfig(BaseModel):
    """Main application configuration."""

    crawler: CrawlerConfig = Field(default_factory=CrawlerConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the configuration to a dictionary."""
        return {
            "crawler": self.crawler.dict(),
            "database": self.database.dict(),
            "llm": self.llm.dict(),
            "storage": self.storage.dict(),
        }


# Create a singleton instance of the configuration
config = AppConfig()


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    return config
