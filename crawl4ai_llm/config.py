"""
Configuration classes for the crawl4ai_llm package.

This module defines Pydantic models for various configuration options.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class StorageConfig(BaseModel):
    """
    Configuration for storage backends.
    
    Attributes:
        type: Storage type (e.g., "json", "sqlite", "mongodb")
        path: Path to the storage directory or connection string
        use_uuid: Whether to use UUIDs for product IDs
        create_if_missing: Whether to create the storage directory if it doesn't exist
        lock_timeout: Timeout for file locking in seconds
        filename_template: Template for generating filenames (JSON storage only)
    """
    
    type: str = Field("json", description="Storage type")
    path: str = Field("./data", description="Storage path or connection string")
    use_uuid: bool = Field(True, description="Use UUIDs for product IDs")
    create_if_missing: bool = Field(True, description="Create storage path if missing")
    lock_timeout: float = Field(30.0, description="Timeout for file locking in seconds")
    filename_template: str = Field("{product_id}.json", description="Template for filenames")
    
    # Additional options for specific storage types
    options: Dict[str, Any] = Field(default_factory=dict, description="Additional options")


class CrawlerConfig(BaseModel):
    """
    Configuration for crawlers.
    
    Attributes:
        user_agent: User agent string for HTTP requests
        timeout: Timeout for HTTP requests in seconds
        max_retries: Maximum number of retries for failed requests
        delay: Delay between requests in seconds
        headers: Additional HTTP headers
        proxy: Proxy URL
        verify_ssl: Whether to verify SSL certificates
    """
    
    user_agent: str = Field(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36",
        description="User agent string"
    )
    timeout: float = Field(30.0, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of retries")
    delay: float = Field(1.0, description="Delay between requests in seconds")
    headers: Dict[str, str] = Field(default_factory=dict, description="Additional HTTP headers")
    proxy: Optional[str] = Field(None, description="Proxy URL")
    verify_ssl: bool = Field(True, description="Verify SSL certificates")
    
    # Additional options
    options: Dict[str, Any] = Field(default_factory=dict, description="Additional options")


class LLMConfig(BaseModel):
    """
    Configuration for LLM-based extraction.
    
    Attributes:
        provider: LLM provider (e.g., "openai", "anthropic", "local")
        model: Model name
        api_key: API key for the provider
        temperature: Temperature for text generation
        max_tokens: Maximum number of tokens to generate
        top_p: Top-p sampling parameter
        cache_dir: Directory for caching LLM responses
    """
    
    provider: str = Field("openai", description="LLM provider")
    model: str = Field("gpt-4", description="Model name")
    api_key: Optional[str] = Field(None, description="API key")
    temperature: float = Field(0.0, description="Temperature for text generation")
    max_tokens: int = Field(4000, description="Maximum tokens to generate")
    top_p: float = Field(1.0, description="Top-p sampling parameter")
    cache_dir: str = Field("./cache", description="Cache directory")
    
    # Additional options
    options: Dict[str, Any] = Field(default_factory=dict, description="Additional options")


class AppConfig(BaseModel):
    """
    Main application configuration.
    
    Attributes:
        storage: Storage configuration
        crawler: Crawler configuration
        llm: LLM configuration
        log_level: Logging level
    """
    
    storage: StorageConfig = Field(default_factory=StorageConfig, description="Storage configuration")
    crawler: CrawlerConfig = Field(default_factory=CrawlerConfig, description="Crawler configuration")
    llm: LLMConfig = Field(default_factory=LLMConfig, description="LLM configuration")
    log_level: str = Field("INFO", description="Logging level")
    
    # Additional settings
    settings: Dict[str, Any] = Field(default_factory=dict, description="Additional settings")