"""
Models for the Crawl4AI LLM client library.

This module defines the Pydantic models used for requests and responses in the client library.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, HttpUrl

from ..models import ProductData


class ExtractionMethod(str, Enum):
    """Extraction methods available for product extraction."""
    
    AUTO = "auto"
    SCHEMA = "schema"
    LLM = "llm"
    HYBRID = "hybrid"


class ExportFormat(str, Enum):
    """Export formats supported by the API."""
    
    JSON = "json"
    CSV = "csv"


class ExtractionRequest(BaseModel):
    """Model for product extraction requests."""
    
    url: HttpUrl = Field(..., description="URL of the product to extract")
    extraction_method: ExtractionMethod = Field(
        default=ExtractionMethod.AUTO, 
        description="Method to use for extraction"
    )
    use_fallback: bool = Field(
        default=True, 
        description="Whether to use fallback extraction if primary method fails"
    )
    store_result: bool = Field(
        default=True, 
        description="Whether to store the extraction result in the database"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Additional metadata to store with the extraction"
    )


class ExtractionResult(BaseModel):
    """Model for product extraction results."""
    
    success: bool = Field(..., description="Whether the extraction was successful")
    product_id: Optional[str] = Field(None, description="ID of the extracted product in storage")
    product: Optional[ProductData] = Field(None, description="Extracted product data")
    messages: List[str] = Field(default_factory=list, description="Messages from the extraction process")
    error: Optional[str] = Field(None, description="Error message if extraction failed")
    extraction_time: Optional[float] = Field(None, description="Time taken for extraction in seconds")


class BatchExtractionResult(BaseModel):
    """Model for batch extraction results."""
    
    results: List[ExtractionResult] = Field(..., description="List of extraction results")
    successful_count: int = Field(..., description="Number of successful extractions")
    failed_count: int = Field(..., description="Number of failed extractions")
    total_time: float = Field(..., description="Total time taken for all extractions in seconds")


class ProductFilter(BaseModel):
    """Model for filtering products in search and export operations."""
    
    title: Optional[str] = Field(None, description="Filter by product title (partial match)")
    brand: Optional[str] = Field(None, description="Filter by brand name (exact match)")
    price_min: Optional[float] = Field(None, description="Minimum price")
    price_max: Optional[float] = Field(None, description="Maximum price")
    created_after: Optional[datetime] = Field(None, description="Filter products created after this time")
    created_before: Optional[datetime] = Field(None, description="Filter products created before this time")
    metadata_filter: Optional[Dict[str, Any]] = Field(None, description="Filter by metadata fields")


class SearchResult(BaseModel):
    """Model for product search results."""
    
    products: List[ProductData] = Field(..., description="List of matching products")
    total: int = Field(..., description="Total number of matching products")
    limit: int = Field(..., description="Limit used for the search")
    offset: int = Field(..., description="Offset used for the search")


class APIError(Exception):
    """Exception raised for API errors."""
    
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API Error ({status_code}): {detail}") 