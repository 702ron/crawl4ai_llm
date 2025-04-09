"""
Data models for the crawl4ai_llm package.

This module defines Pydantic models for representing product data
and related entities.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


class ProductPrice(BaseModel):
    """Model representing a product price."""
    
    amount: str = Field(..., description="Price amount as a string")
    currency: str = Field(..., description="Currency code (e.g., USD, EUR)")
    
    # Optional fields
    original_amount: Optional[str] = Field(None, description="Original price before discount")
    discount_percentage: Optional[float] = Field(None, description="Discount percentage if applicable")
    

class ProductImage(BaseModel):
    """Model representing a product image."""
    
    url: HttpUrl = Field(..., description="URL of the product image")
    alt: Optional[str] = Field(None, description="Alt text for the image")
    position: Optional[int] = Field(None, description="Position in the image list")


class ProductData(BaseModel):
    """
    Model representing product data extracted from e-commerce sites.
    
    This model contains all the relevant information about a product,
    including basic details, prices, images, and additional attributes.
    """
    
    # Required fields
    title: str = Field(..., description="Product title")
    url: HttpUrl = Field(..., description="Product URL")
    
    # Optional basic fields
    description: Optional[str] = Field(None, description="Product description")
    brand: Optional[str] = Field(None, description="Product brand name")
    
    # Price information
    prices: List[ProductPrice] = Field(default_factory=list, description="Product prices")
    
    # Images
    images: List[ProductImage] = Field(default_factory=list, description="Product images")
    
    # Identifiers (SKU, UPC, EAN, etc.)
    identifiers: Dict[str, str] = Field(default_factory=dict, description="Product identifiers")
    
    # Attributes (color, size, material, etc.)
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Product attributes")
    
    # Variants
    variants: List[Dict[str, Any]] = Field(default_factory=list, description="Product variants")
    
    # Availability
    available: Optional[bool] = Field(None, description="Whether the product is in stock")
    availability_text: Optional[str] = Field(None, description="Text describing availability")
    
    # Extraction metadata
    extracted_at: Optional[datetime] = Field(default_factory=datetime.now, description="Extraction timestamp")
    source_html: Optional[str] = Field(None, description="Source HTML content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        """Pydantic model configuration."""
        
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }