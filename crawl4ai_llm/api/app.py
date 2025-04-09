"""
FastAPI application for the Crawl4AI LLM product extraction system.
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

from ..extraction.product_extractor import ProductExtractor
from ..extraction.schema_generator import SchemaGenerator
from ..models import ProductData
from ..storage import get_storage, StorageError, ProductNotFoundError, DuplicateProductError
from ..config import get_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Crawl4AI LLM API",
    description="API for extracting product data from e-commerce websites using LLMs",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Can be set to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request and response models
class ExtractionRequest(BaseModel):
    url: HttpUrl
    strategy: str = "auto"
    fallback: bool = True
    cache: bool = True

class ExtractionResponse(BaseModel):
    url: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]

class ConfigurationResponse(BaseModel):
    crawler: dict
    database: dict
    llm: dict
    storage: dict

class ProductResponse(BaseModel):
    id: str
    title: str
    brand: Optional[str] = None
    price: Dict[str, Any]
    url: Optional[str] = None
    images: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}

# Helper to get ProductExtractor
def get_extractor():
    config = get_config()
    return ProductExtractor()

# Helper to get storage instance
def get_storage_instance():
    """Get the storage instance using the factory pattern."""
    return get_storage()

# Routes
@app.get("/")
async def root():
    """Root endpoint returning API information."""
    return {
        "name": "Crawl4AI LLM API",
        "version": "0.1.0",
        "description": "API for extracting product data from e-commerce websites using LLMs",
    }

@app.get("/config", response_model=ConfigurationResponse)
async def get_configuration():
    """Get the current configuration."""
    config = get_config()
    return {
        "crawler": config.crawler.dict(),
        "database": config.database.dict(),
        "llm": config.llm.dict(),
        "storage": config.storage.dict(),
    }

@app.post("/extract", response_model=ExtractionResponse)
async def extract_product(
    request: ExtractionRequest,
    extractor=Depends(get_extractor),
    storage=Depends(get_storage_instance)
):
    """Extract product data from a URL."""
    try:
        start_time = datetime.now()
        
        # Extract the product data
        result = await extractor.extract(
            url=str(request.url),
            strategy=request.strategy,
            fallback=request.fallback,
            use_cache=request.cache
        )
        
        # Create a response with metadata
        end_time = datetime.now()
        extraction_time = (end_time - start_time).total_seconds()
        
        response_data = {
            "url": str(request.url),
            "data": result.dict(),
            "metadata": {
                "extraction_time": extraction_time,
                "strategy": request.strategy,
                "fallback_used": request.fallback,
                "timestamp": end_time.isoformat(),
            }
        }
        
        # Store the result
        try:
            product_id = await storage.save_product(result)
            response_data["metadata"]["product_id"] = product_id
        except DuplicateProductError:
            logger.warning(f"Product already exists in storage: {result.title}")
            response_data["metadata"]["storage_status"] = "already_exists"
        except StorageError as e:
            logger.error(f"Failed to save product to storage: {str(e)}")
            response_data["metadata"]["storage_status"] = "failed"
        
        return response_data
    
    except Exception as e:
        logger.error(f"Error extracting product: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

@app.get("/products", response_model=List[ProductResponse])
async def list_products(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    brand: Optional[str] = None,
    sort_by: Optional[str] = Query(None, description="Field to sort by (title, brand, etc.)"),
    sort_order: str = Query("asc", description="Sort order (asc or desc)"),
    storage=Depends(get_storage_instance)
):
    """List stored products with optional filtering and sorting."""
    try:
        # Build filters if any are provided
        filters = {}
        if brand:
            filters["brand"] = brand
            
        # Get products from storage
        products, total_count = await storage.list_products(
            filters=filters,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # Format for API response
        result = []
        for product in products:
            product_dict = product.dict()
            # Extract metadata from the product
            metadata = product_dict.pop("raw_data", {}) or {}
            metadata.update(product_dict.pop("extracted_at", {}))
            metadata.update({"total_count": total_count})
            
            # Add product ID from metadata if available
            product_id = metadata.get("product_id", "unknown")
            
            result.append({
                "id": product_id,
                "title": product.title,
                "brand": product.brand,
                "price": product.price.dict(),
                "url": product.url,
                "images": [img.dict() for img in product.images],
                "metadata": metadata
            })
            
        return result
    except StorageError as e:
        logger.error(f"Error listing products: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list products: {str(e)}")

@app.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str, storage=Depends(get_storage_instance)):
    """Get a specific product by ID."""
    try:
        product = await storage.get_product(product_id)
        
        # Format for API response
        product_dict = product.dict()
        # Extract metadata from the product
        metadata = product_dict.pop("raw_data", {}) or {}
        metadata.update(product_dict.pop("extracted_at", {}))
        
        return {
            "id": product_id,
            "title": product.title,
            "brand": product.brand,
            "price": product.price.dict(),
            "url": product.url,
            "images": [img.dict() for img in product.images],
            "metadata": metadata
        }
    except ProductNotFoundError:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    except StorageError as e:
        logger.error(f"Error retrieving product {product_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve product: {str(e)}")

@app.delete("/products/{product_id}")
async def delete_product(product_id: str, storage=Depends(get_storage_instance)):
    """Delete a specific product by ID."""
    try:
        await storage.delete_product(product_id)
        return {"status": "success", "message": f"Product {product_id} deleted"}
    except ProductNotFoundError:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    except StorageError as e:
        logger.error(f"Error deleting product {product_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete product: {str(e)}")

@app.get("/schema")
async def generate_schema(
    url: HttpUrl = Query(..., description="URL of the product page")
):
    """Generate extraction schema for a product page."""
    try:
        config = get_config()
        schema_generator = SchemaGenerator()
        schema = await schema_generator.generate_schema(str(url))
        return {"url": str(url), "schema": schema}
    except Exception as e:
        logger.error(f"Error generating schema: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Schema generation failed: {str(e)}")

def start_server(host: str = "127.0.0.1", port: int = 8000, reload: bool = False):
    """Start the FastAPI server using uvicorn."""
    try:
        uvicorn.run(
            "crawl4ai_llm.api.app:app",
            host=host,
            port=port,
            reload=reload,
        )
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise 