"""
Crawl4AI SDK - Python Client Library

A simple and powerful client for extracting, managing, and searching product data
using the Crawl4AI service.
"""

from .client import Crawl4AIClient
from .models import (
    ExtractionRequest, 
    ExtractionMethod,
    ProductFilter, 
    ExportFormat,
    ProductData,
    ProductImage,
    ProductPrice,
    ProductAttribute,
    ProductVariant,
    ProductReview,
    ExtractionResult,
    BatchExtractionResult,
    SearchResult,
    APIError
)
from .sync_client import SyncCrawl4AIClient

__version__ = "0.1.0"
__all__ = [
    # Clients
    "Crawl4AIClient",
    "SyncCrawl4AIClient",
    
    # Request models
    "ExtractionRequest",
    "ExtractionMethod",
    "ProductFilter",
    "ExportFormat",
    
    # Data models
    "ProductData",
    "ProductImage",
    "ProductPrice",
    "ProductAttribute",
    "ProductVariant",
    "ProductReview",
    
    # Response models
    "ExtractionResult",
    "BatchExtractionResult",
    "SearchResult",
    
    # Errors
    "APIError"
] 