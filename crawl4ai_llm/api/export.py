"""
Export functionality for the Crawl4AI LLM API.

This module provides utilities for exporting product data to various formats,
including CSV and JSON.
"""

import csv
import io
import json
import logging
from typing import Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response, StreamingResponse

from ..models import ProductData
from ..storage import StorageError, get_storage
from .auth import User, check_rate_limit

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/export",
    tags=["Export"],
    dependencies=[Depends(check_rate_limit)],
)


def _flatten_product(product: ProductData) -> Dict:
    """Flatten a ProductData object for CSV export."""
    # Start with basic fields
    flat_data = {
        "title": product.title,
        "description": product.description if product.description else "",
        "url": product.url if product.url else "",
        "brand": product.brand if product.brand else "",
        "currency": product.price.currency if product.price else "",
        "price": product.price.value if product.price else "",
        "availability": product.availability if product.availability else "",
        "rating": product.rating if product.rating else "",
        "reviews_count": product.reviews_count if product.reviews_count else "",
        "id": product.id if product.id else "",
        "sku": product.sku if product.sku else "",
        "upc": product.upc if product.upc else "",
        "ean": product.ean if product.ean else "",
        "mpn": product.mpn if product.mpn else "",
        "gtin": product.gtin if product.gtin else "",
    }

    # Handle images
    if product.images:
        # Get primary image
        flat_data["primary_image"] = product.images[0].url if product.images else ""
        
        # Add additional images
        for i, img in enumerate(product.images[1:], 1):
            if i > 5:  # Limit to 5 additional images
                break
            flat_data[f"image_{i}"] = img.url

    # Handle attributes
    if product.attributes:
        for attr in product.attributes:
            key = f"attr_{attr.name}".replace(" ", "_").lower()
            flat_data[key] = attr.value

    # Handle variants
    if product.variants:
        for i, variant in enumerate(product.variants[:5], 1):  # Limit to 5 variants
            flat_data[f"variant_{i}_name"] = variant.name if variant.name else ""
            flat_data[f"variant_{i}_price"] = variant.price.value if variant.price else ""
            flat_data[f"variant_{i}_currency"] = variant.price.currency if variant.price else ""
            flat_data[f"variant_{i}_availability"] = variant.availability if variant.availability else ""

    # Handle dimensions
    if product.dimensions:
        flat_data["dimension_width"] = product.dimensions.width if product.dimensions.width else ""
        flat_data["dimension_height"] = product.dimensions.height if product.dimensions.height else ""
        flat_data["dimension_depth"] = product.dimensions.depth if product.dimensions.depth else ""
        flat_data["dimension_weight"] = product.dimensions.weight if product.dimensions.weight else ""
        flat_data["dimension_unit"] = product.dimensions.unit if product.dimensions.unit else ""
        flat_data["dimension_weight_unit"] = product.dimensions.weight_unit if product.dimensions.weight_unit else ""

    return flat_data


@router.get("/csv")
async def export_to_csv(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    brand: Optional[str] = None,
    user: User = Depends(check_rate_limit),
):
    """Export products to CSV format."""
    try:
        # Get storage
        storage = get_storage()

        # Build filters
        filters = {}
        if brand:
            filters["brand"] = brand

        # Get products
        products, total_count = await storage.list_products(
            filters=filters, limit=limit, offset=offset
        )

        if not products:
            return Response(
                content="No products found matching your criteria",
                media_type="text/plain",
            )

        # Prepare CSV output
        output = io.StringIO()
        
        # Get all possible fields by combining all flattened products
        all_fields = set()
        flattened_products = []
        
        for product in products:
            flat_product = _flatten_product(product)
            flattened_products.append(flat_product)
            all_fields.update(flat_product.keys())
        
        # Create sorted list of field names
        fieldnames = sorted(list(all_fields))
        
        # Write CSV
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(flattened_products)
        
        # Prepare response
        output.seek(0)
        
        return StreamingResponse(
            io.StringIO(output.getvalue()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=products_export.csv"}
        )
    
    except StorageError as e:
        logger.error(f"Error exporting products to CSV: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export products: {str(e)}",
        )


@router.get("/json")
async def export_to_json(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    brand: Optional[str] = None,
    pretty: bool = Query(False, description="Pretty print the JSON output"),
    flatten: bool = Query(False, description="Flatten the product data structure"),
    user: User = Depends(check_rate_limit),
):
    """Export products to JSON format."""
    try:
        # Get storage
        storage = get_storage()

        # Build filters
        filters = {}
        if brand:
            filters["brand"] = brand

        # Get products
        products, total_count = await storage.list_products(
            filters=filters, limit=limit, offset=offset
        )

        if not products:
            return Response(
                content=json.dumps({"products": [], "total": 0}),
                media_type="application/json",
            )

        # Prepare data
        if flatten:
            # Use the flattened structure for compatibility with CSV
            product_data = [_flatten_product(p) for p in products]
        else:
            # Use the full structure
            product_data = [p.dict(exclude_none=True) for p in products]
        
        # Prepare output
        output = {
            "products": product_data,
            "total": total_count,
            "limit": limit,
            "offset": offset,
        }
        
        # Convert to JSON
        indent = 2 if pretty else None
        json_data = json.dumps(output, indent=indent)
        
        return Response(
            content=json_data,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=products_export.json"}
        )
    
    except StorageError as e:
        logger.error(f"Error exporting products to JSON: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export products: {str(e)}",
        ) 