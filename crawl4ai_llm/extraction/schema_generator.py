"""
Schema generator for product extraction.

This module provides functionality to generate extraction schemas
from HTML content by analyzing common patterns in e-commerce sites.
"""

import re
import json
import logging
import os
from typing import Dict, List, Optional, Set, Any, Union, Tuple
from bs4 import BeautifulSoup
import hashlib

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

from ..config import config
from ..prompts.product_extraction import SCHEMA_GENERATION_PROMPT
from .schema_validator import COMMON_PRODUCT_ATTRIBUTES, SchemaValidator, validate_extraction_schema, correct_extraction_schema

# Set up logging
logger = logging.getLogger(__name__)

# Common selectors for product elements
COMMON_SELECTORS = {
    "title": [
        "h1", 
        "[itemprop='name']", 
        ".product-title", 
        ".product-name", 
        ".product-heading"
    ],
    "price": [
        "[itemprop='price']",
        "[data-price]",
        ".price",
        ".product-price",
        ".current-price",
        ".sale-price",
        "span.amount"
    ],
    "description": [
        "[itemprop='description']",
        "#description",
        ".product-description",
        ".description",
        ".product-details",
        "#product-description"
    ],
    "brand": [
        "[itemprop='brand']",
        ".brand",
        ".product-brand",
        "[data-brand]"
    ],
    "image": [
        "[itemprop='image']",
        ".product-image img",
        ".main-image img",
        "#main-product-image"
    ],
    "images": [
        ".product-gallery img",
        ".product-images img",
        ".thumbnail-images img",
        ".gallery img"
    ],
    "sku": [
        "[itemprop='sku']",
        "[data-sku]",
        ".sku",
        ".product-sku",
        "#product-sku"
    ],
    "availability": [
        "[itemprop='availability']",
        ".availability",
        ".stock-status",
        ".product-availability",
        "[data-availability]"
    ]
}

# Keywords likely to be associated with product features
ATTRIBUTE_KEYWORDS = {
    "title": ["product", "title", "name", "heading"],
    "price": ["price", "cost", "amount", "sale", "discount"],
    "description": ["description", "details", "about", "overview", "summary"],
    "brand": ["brand", "manufacturer", "make", "company"],
    "image": ["image", "img", "photo", "picture", "main-image"],
    "images": ["gallery", "thumbnails", "images", "pictures", "photos"],
    "sku": ["sku", "item", "product", "code", "number"],
    "availability": ["availability", "stock", "in stock", "out of stock", "inventory"],
    "rating": ["rating", "stars", "score", "reviews"],
    "reviews": ["reviews", "testimonials", "comments", "feedback"],
    "categories": ["categories", "category", "department", "section"]
}


class SchemaGenerator:
    """
    Generates extraction schemas from HTML content.
    
    This class analyzes HTML content to generate extraction schemas
    based on common patterns found in e-commerce websites.
    """
    
    def __init__(self, cache_dir: Optional[str] = None, validator: Optional[SchemaValidator] = None):
        """
        Initialize the schema generator.
        
        Args:
            cache_dir: Directory for caching generated schemas. If None, uses config value.
            validator: Schema validator instance. If None, creates a new one.
        """
        self.cache_dir = cache_dir or os.path.join(config.crawler.cache_dir, "schemas")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.validator = validator or SchemaValidator()
        
    def _get_cache_key(self, url: str, html: str) -> str:
        """
        Generate a cache key for the schema.
        
        Args:
            url: URL of the product page.
            html: HTML content of the page.
            
        Returns:
            str: Cache key for the schema.
        """
        # Use domain and HTML structure to create a unique key
        domain = url.split("/")[2]  # Extract domain from URL
        html_hash = hashlib.md5(html.encode()).hexdigest()
        return f"{domain}_{html_hash[:10]}"
    
    def _get_cache_path(self, cache_key: str) -> str:
        """
        Get the file path for a cached schema.
        
        Args:
            cache_key: Cache key for the schema.
            
        Returns:
            str: File path for the cached schema.
        """
        return os.path.join(self.cache_dir, f"{cache_key}.json")
    
    def _cache_schema(self, cache_key: str, schema: Dict[str, Any]) -> None:
        """
        Cache a generated schema.
        
        Args:
            cache_key: Cache key for the schema.
            schema: Generated schema to cache.
        """
        cache_path = self._get_cache_path(cache_key)
        try:
            with open(cache_path, "w") as f:
                json.dump(schema, f, indent=2)
            logger.debug(f"Cached schema to {cache_path}")
        except Exception as e:
            logger.error(f"Error caching schema: {str(e)}")
    
    def _get_cached_schema(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get a cached schema if available.
        
        Args:
            cache_key: Cache key for the schema.
            
        Returns:
            Optional[Dict[str, Any]]: Cached schema if available, None otherwise.
        """
        cache_path = self._get_cache_path(cache_key)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading cached schema: {str(e)}")
        return None
    
    def validate_and_correct_schema(self, schema: Dict[str, Any], url: str) -> Tuple[Dict[str, Any], bool, List[str]]:
        """
        Validate a schema and correct it if necessary.
        
        Args:
            schema: The schema to validate and correct.
            url: The URL for the schema (for logging purposes).
            
        Returns:
            Tuple containing:
                - Dict[str, Any]: The validated and potentially corrected schema.
                - bool: Whether the schema needed correction.
                - List[str]: List of corrections or validation errors.
        """
        # Validate the schema
        is_valid, errors = self.validator.validate_schema(schema)
        
        if is_valid:
            logger.debug(f"Schema for {url} is valid")
            return schema, False, []
            
        # Schema is invalid, try to correct it
        logger.warning(f"Schema for {url} is invalid: {', '.join(errors)}")
        corrected_schema, corrections = self.validator.correct_schema(schema)
        
        if corrections:
            logger.info(f"Schema for {url} was corrected: {', '.join(corrections)}")
            
            # Validate again to ensure corrections fixed all issues
            is_valid, remaining_errors = self.validator.validate_schema(corrected_schema)
            
            if not is_valid:
                logger.warning(f"Corrected schema for {url} still has issues: {', '.join(remaining_errors)}")
                return corrected_schema, True, corrections + remaining_errors
                
            return corrected_schema, True, corrections
            
        logger.error(f"Schema for {url} could not be corrected")
        return schema, False, errors
        
    def generate_schema_report(self, schema: Dict[str, Any], url: str) -> Dict[str, Any]:
        """
        Generate a report on schema quality.
        
        Args:
            schema: The schema to analyze.
            url: The URL for the schema (included in the report).
            
        Returns:
            Dict[str, Any]: A report with schema statistics and improvement suggestions.
        """
        report = self.validator.generate_schema_report(schema)
        report["url"] = url
        report["timestamp"] = config.app.get_timestamp()
        return report
    
    async def generate_schema(
        self, 
        url: str, 
        html: Optional[str] = None,
        use_cache: bool = True,
        provider: Optional[str] = None,
        api_token: Optional[str] = None,
        auto_correct: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate an extraction schema for a product page.
        
        Args:
            url: URL of the product page.
            html: HTML content of the page. If None, will be fetched.
            use_cache: Whether to use cached schemas.
            provider: LLM provider to use. If None, uses config value.
            api_token: API token for LLM provider. If None, uses config value.
            auto_correct: Whether to automatically correct invalid schemas.
            
        Returns:
            Dict[str, Any]: Generated extraction schema.
        """
        # If HTML is not provided, fetch it
        if html is None:
            browser_config = BrowserConfig(headless=config.crawler.headless)
            crawler_config = CrawlerRunConfig(cache_mode=CacheMode.ENABLED)
            
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=url, config=crawler_config)
                html = result.html
        
        # Check cache if enabled
        if use_cache:
            cache_key = self._get_cache_key(url, html)
            cached_schema = self._get_cached_schema(cache_key)
            if cached_schema:
                logger.info(f"Using cached schema for {url}")
                # Even for cached schemas, validate and correct if necessary
                if auto_correct:
                    validated_schema, was_corrected, _ = self.validate_and_correct_schema(cached_schema, url)
                    if was_corrected:
                        logger.info(f"Corrected cached schema for {url}")
                        self._cache_schema(cache_key, validated_schema)
                        return validated_schema
                return cached_schema
        
        # Set up LLM provider details
        provider = provider or f"{config.llm.provider}/{config.llm.model}"
        api_token = api_token or config.llm.api_key
        
        # Create extraction strategy for schema generation
        logger.info(f"Generating schema for {url} using {provider}")
        extraction_strategy = JsonCssExtractionStrategy(
            provider=provider,
            api_token=api_token
        )
        
        # Generate schema using Crawl4AI
        try:
            schema = await extraction_strategy.generate_schema(
                html=html,
                schema_name="E-commerce Product Data",
                instruction=SCHEMA_GENERATION_PROMPT,
                extra_args={
                    "temperature": config.llm.temperature,
                    "max_tokens": config.llm.max_tokens,
                }
            )
            
            # Validate and correct schema if necessary
            if auto_correct:
                schema, was_corrected, _ = self.validate_and_correct_schema(schema, url)
                
            # Cache the generated schema
            if use_cache:
                cache_key = self._get_cache_key(url, html)
                self._cache_schema(cache_key, schema)
                
            return schema
            
        except Exception as e:
            logger.error(f"Error generating schema for {url}: {str(e)}")
            
            # In case of error, try to create a basic schema
            basic_schema = {
                "fields": [
                    {
                        "name": "title",
                        "selector": "h1",
                        "required": True,
                        "description": "Product title/name"
                    },
                    {
                        "name": "price.current_price",
                        "selector": ".price, [data-price], .product-price",
                        "required": True,
                        "description": "Current product price"
                    },
                    {
                        "name": "price.currency",
                        "selector": ".currency",
                        "description": "Currency code or symbol",
                        "required": True
                    },
                    {
                        "name": "description",
                        "selector": ".product-description, [itemprop='description']",
                        "description": "Product description"
                    },
                    {
                        "name": "images",
                        "selector": ".product-image, [itemprop='image']",
                        "attribute": "src",
                        "array": True,
                        "description": "Product images"
                    }
                ]
            }
            
            logger.info(f"Using fallback basic schema for {url}")
            
            # Cache the basic schema if requested
            if use_cache:
                cache_key = self._get_cache_key(url, html)
                self._cache_schema(cache_key, basic_schema)
                
            return basic_schema 


def generate_schema_from_html(html_content: str) -> Dict[str, Any]:
    """
    Generate an extraction schema from HTML content.
    
    Args:
        html_content: The HTML content to analyze.
        
    Returns:
        A dictionary containing the generated schema.
    """
    generator = SchemaGenerator()
    return generator.generate()


def validate_and_enhance_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and enhance an existing schema, ensuring it has proper structure.
    
    Args:
        schema: The schema to validate and enhance.
        
    Returns:
        The validated and enhanced schema.
    """
    validator = SchemaValidator()
    is_valid, errors = validator.validate(schema)
    
    if not is_valid:
        logger.info(f"Schema needs correction: {errors}")
        schema = validator.correct_schema(schema)
        
    return schema 