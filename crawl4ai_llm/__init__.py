"""
Crawl4AI LLM-based product extraction toolkit.
"""

__version__ = "0.1.0"

from .config import AppConfig, CrawlerConfig, LLMConfig, StorageConfig, get_config
from .models import ProductData, ProductPrice, ProductImage, ProductAttribute, ProductReview
from .extraction import ProductExtractor, SchemaGenerator
from .processing import DataProcessor
from .storage import BaseStorage, JSONStorage, get_storage

__all__ = [
    "AppConfig", "CrawlerConfig", "LLMConfig", "StorageConfig", "get_config",
    "ProductData", "ProductPrice", "ProductImage", "ProductAttribute", "ProductReview",
    "ProductExtractor", "SchemaGenerator",
    "DataProcessor",
    "BaseStorage", "JSONStorage", "get_storage",
] 