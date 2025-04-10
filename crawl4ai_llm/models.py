"""
Pydantic models for product data extraction.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class ProductImage(BaseModel):
    """Model for product images."""

    url: HttpUrl = Field(..., description="URL of the product image")
    alt_text: Optional[str] = Field(None, description="Alternative text for the image")
    position: Optional[int] = Field(
        None, description="Position/order of the image in the product gallery"
    )


class ProductPrice(BaseModel):
    """Model for product price information."""

    current_price: float = Field(..., description="Current price of the product")
    currency: str = Field(..., description="Currency code (e.g., USD, EUR)")
    original_price: Optional[float] = Field(
        None, description="Original/list price before any discounts"
    )
    discount_percentage: Optional[float] = Field(
        None, description="Discount percentage if on sale"
    )
    discount_amount: Optional[float] = Field(
        None, description="Discount amount if on sale"
    )
    price_per_unit: Optional[str] = Field(
        None, description="Price per unit for measurement-based products"
    )


class ProductAttribute(BaseModel):
    """Model for product attributes like color, size, material, etc."""

    name: str = Field(..., description="Name of the attribute")
    value: str = Field(..., description="Value of the attribute")


class ProductVariant(BaseModel):
    """Model for product variants (e.g., different sizes, colors)."""

    id: Optional[str] = Field(None, description="Variant ID or SKU")
    name: Optional[str] = Field(None, description="Name of the variant")
    attributes: List[ProductAttribute] = Field(
        default_factory=list, description="List of variant attributes"
    )
    price: Optional[ProductPrice] = Field(
        None, description="Price of this specific variant"
    )
    image: Optional[ProductImage] = Field(
        None, description="Image specific to this variant"
    )
    availability: Optional[str] = Field(
        None, description="Availability status of this variant"
    )


class ProductReview(BaseModel):
    """Model for product reviews."""

    reviewer_name: Optional[str] = Field(None, description="Name of the reviewer")
    rating: Optional[float] = Field(None, description="Rating given by the reviewer")
    title: Optional[str] = Field(None, description="Title of the review")
    content: Optional[str] = Field(None, description="Content of the review")
    date: Optional[str] = Field(None, description="Date when the review was posted")
    verified_purchase: Optional[bool] = Field(
        None, description="Whether this is a verified purchase"
    )


class ProductData(BaseModel):
    """Primary model for extracted product data."""

    title: str = Field(..., description="Product title/name")
    description: Optional[str] = Field(None, description="Full product description")
    short_description: Optional[str] = Field(
        None, description="Short product description or subtitle"
    )
    brand: Optional[str] = Field(None, description="Brand name of the product")
    price: ProductPrice = Field(..., description="Product price information")
    images: List[ProductImage] = Field(
        default_factory=list, description="List of product images"
    )

    # Product identifiers
    sku: Optional[str] = Field(None, description="Stock Keeping Unit")
    upc: Optional[str] = Field(None, description="Universal Product Code")
    ean: Optional[str] = Field(None, description="European Article Number")
    isbn: Optional[str] = Field(None, description="International Standard Book Number")
    mpn: Optional[str] = Field(None, description="Manufacturer Part Number")
    gtin: Optional[str] = Field(None, description="Global Trade Item Number")

    # Additional data
    category: Optional[List[str]] = Field(
        None, description="Product categories as a breadcrumb path"
    )
    availability: Optional[str] = Field(None, description="Product availability status")
    url: Optional[HttpUrl] = Field(None, description="URL of the product page")
    rating: Optional[float] = Field(None, description="Average product rating")
    review_count: Optional[int] = Field(None, description="Number of reviews")
    reviews: Optional[List[ProductReview]] = Field(
        None, description="List of product reviews"
    )
    variants: Optional[List[ProductVariant]] = Field(
        None, description="List of product variants"
    )
    attributes: Optional[List[ProductAttribute]] = Field(
        None, description="List of product attributes"
    )
    
    # Enhanced metadata fields
    shipping_info: Optional[str] = Field(None, description="Information about shipping options")
    warranty: Optional[str] = Field(None, description="Warranty information")
    dimensions: Optional[str] = Field(None, description="Product dimensions")
    weight: Optional[str] = Field(None, description="Product weight")
    material: Optional[str] = Field(None, description="Product material")
    seller: Optional[str] = Field(None, description="Seller or manufacturer information")
    release_date: Optional[str] = Field(None, description="Product launch or release date")

    # Metadata
    extracted_at: Optional[str] = Field(
        None, description="Timestamp of when the data was extracted"
    )
    source: Optional[str] = Field(None, description="Source website or platform")
    raw_data: Optional[Dict[str, Any]] = Field(
        None, description="Raw extracted data before processing"
    )
    extraction_success: bool = Field(
        True, description="Whether the extraction was successful"
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "title": "Apple iPhone 13 Pro - 256GB - Graphite",
                "description": "The iPhone 13 Pro features a 6.1-inch Super Retina XDR display with ProMotion...",
                "brand": "Apple",
                "price": {
                    "current_price": 999.99,
                    "currency": "USD",
                    "original_price": 1099.99,
                    "discount_percentage": 9.09,
                },
                "images": [
                    {
                        "url": "https://example.com/images/iphone-13-pro-1.jpg",
                        "alt_text": "iPhone 13 Pro Front View",
                        "position": 1,
                    }
                ],
                "sku": "IP13P-256-GR",
                "upc": "123456789012",
                "availability": "In Stock",
                "url": "https://example.com/products/iphone-13-pro",
                "rating": 4.8,
                "review_count": 2547,
            }
        }
