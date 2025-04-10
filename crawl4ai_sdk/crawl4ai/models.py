"""
Models for the Crawl4AI SDK.

This module defines the Pydantic models used for requests and responses in the SDK.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, HttpUrl, validator


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


class ProductImage(BaseModel):
    """Model for product image data."""
    
    url: HttpUrl = Field(..., description="URL of the product image")
    alt_text: Optional[str] = Field(None, description="Alternative text for the image")
    position: Optional[int] = Field(None, description="Position of the image in the product gallery")


class ProductPrice(BaseModel):
    """Model for product price data."""
    
    current: float = Field(..., description="Current price of the product")
    currency: str = Field(..., description="Currency code (e.g., USD, EUR)")
    original: Optional[float] = Field(None, description="Original price before discount")
    sale_percentage: Optional[float] = Field(None, description="Percentage of price reduction if on sale")


class ProductAttribute(BaseModel):
    """Model for product attributes."""
    
    name: str = Field(..., description="Name of the attribute")
    value: Any = Field(..., description="Value of the attribute")
    unit: Optional[str] = Field(None, description="Unit of measurement if applicable")


class ProductVariant(BaseModel):
    """Model for product variants."""
    
    id: Optional[str] = Field(None, description="ID of the variant")
    name: str = Field(..., description="Name of the variant")
    attributes: List[ProductAttribute] = Field(default_factory=list, description="Attributes of the variant")
    price: Optional[ProductPrice] = Field(None, description="Price of the variant")
    availability: Optional[str] = Field(None, description="Availability status of the variant")
    image_url: Optional[HttpUrl] = Field(None, description="URL of the variant image")


class ProductReview(BaseModel):
    """Model for product reviews."""
    
    rating: float = Field(..., description="Rating value")
    count: Optional[int] = Field(None, description="Number of reviews")
    source: Optional[str] = Field(None, description="Source of the review data")


class ProductData(BaseModel):
    """Model for extracted product data."""
    
    # Basic product information
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: Optional[ProductPrice] = Field(None, description="Product price information")
    brand: Optional[str] = Field(None, description="Brand name")
    images: Optional[List[ProductImage]] = Field(None, description="Product images")
    
    # Product identifiers
    sku: Optional[str] = Field(None, description="Stock Keeping Unit")
    mpn: Optional[str] = Field(None, description="Manufacturer Part Number")
    gtin: Optional[str] = Field(None, description="Global Trade Item Number")
    upc: Optional[str] = Field(None, description="Universal Product Code")
    ean: Optional[str] = Field(None, description="European Article Number")
    isbn: Optional[str] = Field(None, description="International Standard Book Number")
    
    # Additional product data
    category: Optional[str] = Field(None, description="Product category")
    subcategory: Optional[str] = Field(None, description="Product subcategory")
    url: Optional[HttpUrl] = Field(None, description="Product URL")
    currency: Optional[str] = Field(None, description="Currency code")
    availability: Optional[str] = Field(None, description="Product availability status")
    condition: Optional[str] = Field(None, description="Product condition (new, used, etc.)")
    
    # Optional product data
    attributes: Optional[List[ProductAttribute]] = Field(None, description="Product attributes")
    variants: Optional[List[ProductVariant]] = Field(None, description="Product variants")
    reviews: Optional[ProductReview] = Field(None, description="Product review information")
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    extracted_at: Optional[datetime] = Field(None, description="Timestamp of extraction")


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