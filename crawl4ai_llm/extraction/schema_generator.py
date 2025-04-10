"""
Schema generator for product extraction.

This module provides functionality to generate extraction schemas
from HTML content by analyzing common patterns in e-commerce sites.
"""

import hashlib
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from bs4 import BeautifulSoup
from crawl4ai import (AsyncWebCrawler, BrowserConfig, CacheMode,
                      CrawlerRunConfig)
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

from ..config import config
from ..prompts.product_extraction import SCHEMA_GENERATION_PROMPT
from .schema_validator import (COMMON_PRODUCT_ATTRIBUTES, SchemaValidator,
                               correct_extraction_schema,
                               validate_extraction_schema)

from crawl4ai_llm.crawler.base import BaseCrawler

# Set up logging
logger = logging.getLogger(__name__)

# Common selectors for product elements
COMMON_SELECTORS = {
    "title": [
        "h1",
        "[itemprop='name']",
        ".product-title",
        ".product-name",
        ".product-heading",
    ],
    "price": [
        "[itemprop='price']",
        "[data-price]",
        ".price",
        ".product-price",
        ".current-price",
        ".sale-price",
        "span.amount",
    ],
    "description": [
        "[itemprop='description']",
        "#description",
        ".product-description",
        ".description",
        ".product-details",
        "#product-description",
    ],
    "brand": ["[itemprop='brand']", ".brand", ".product-brand", "[data-brand]"],
    "image": [
        "[itemprop='image']",
        ".product-image img",
        ".main-image img",
        "#main-product-image",
    ],
    "images": [
        ".product-gallery img",
        ".product-images img",
        ".thumbnail-images img",
        ".gallery img",
    ],
    "sku": ["[itemprop='sku']", "[data-sku]", ".sku", ".product-sku", "#product-sku"],
    "availability": [
        "[itemprop='availability']",
        ".availability",
        ".stock-status",
        ".product-availability",
        "[data-availability]",
    ],
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
    "categories": ["categories", "category", "department", "section"],
}


class SchemaGenerator:
    """
    Generates extraction schemas from HTML content.

    This class analyzes HTML content to generate extraction schemas
    based on common patterns found in e-commerce websites.
    """

    def __init__(
        self,
        validate_schema: bool = True,
        auto_correct: bool = True,
        retry_with_fallback: bool = True,
    ):
        """
        Initialize the schema generator.

        Args:
            validate_schema: Whether to validate generated schemas
            auto_correct: Whether to automatically correct invalid schemas
            retry_with_fallback: Whether to retry with fallback methods if primary generation fails
        """
        self.validator = SchemaValidator()
        self.validate_schema = validate_schema
        self.auto_correct = auto_correct
        self.retry_with_fallback = retry_with_fallback

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
        return os.path.join(config.crawler.cache_dir, "schemas", f"{cache_key}.json")

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

    def validate_and_correct_schema(
        self, schema: Dict[str, Any], url: str
    ) -> Tuple[Dict[str, Any], bool, List[str]]:
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
            is_valid, remaining_errors = self.validator.validate_schema(
                corrected_schema
            )

            if not is_valid:
                logger.warning(
                    f"Corrected schema for {url} still has issues: {', '.join(remaining_errors)}"
                )
                return corrected_schema, True, corrections + remaining_errors

            return corrected_schema, True, corrections

        logger.error(f"Schema for {url} could not be corrected")
        return schema, False, errors

    def generate_schema_report(
        self, schema: Dict[str, Any], url: str
    ) -> Dict[str, Any]:
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

    async def generate_schema_from_url(
        self, url: str, crawler: Optional[BaseCrawler] = None
    ) -> Tuple[Dict[str, Any], bool, List[str]]:
        """
        Generate a schema for product extraction from a URL.

        Args:
            url: The URL to generate a schema for
            crawler: Optional crawler instance to use

        Returns:
            A tuple of (schema, success flag, error messages)
        """
        # Create a crawler if one wasn't provided
        if crawler is None:
            crawler = BaseCrawler()

        # Crawl the page
        try:
            result = await crawler.crawl(url)
            if not result.get("success", False):
                return {}, False, ["Failed to crawl URL"]

            html_content = result.get("content", "")
            if not html_content:
                return {}, False, ["No HTML content found"]

            return await self.generate_schema_from_html(html_content)
        except Exception as e:
            logger.error(f"Error generating schema from URL: {e}")
            return {}, False, [f"Error: {str(e)}"]

    async def generate_schema_from_html(
        self, html_content: str
    ) -> Tuple[Dict[str, Any], bool, List[str]]:
        """
        Generate a schema for product extraction from HTML content.

        Args:
            html_content: The HTML content to analyze

        Returns:
            A tuple of (schema, success flag, error messages)
        """
        # Generate initial schema using auto schema extractor
        try:
            schema = await self._generate_schema_with_auto_extractor(html_content)
            if not schema:
                return {}, False, ["Failed to generate schema with auto extractor"]

            # Validate the schema if requested
            if self.validate_schema:
                is_valid = self.validator.validate(schema)
                errors = self.validator.errors

                if not is_valid and self.auto_correct:
                    schema = self.validator.correct_schema(schema)
                    is_valid = self.validator.validate(schema)
                    remaining_errors = self.validator.errors
                    
                    return schema, is_valid, remaining_errors

                return schema, is_valid, errors

            return schema, True, []
        except Exception as e:
            logger.error(f"Error generating schema from HTML: {e}")
            return {}, False, [f"Error: {str(e)}"]

    async def _generate_schema_with_auto_extractor(
        self, html_content: str
    ) -> Dict[str, Any]:
        """
        Generate a schema using BeautifulSoup and pattern matching.
        This implementation replaces the need for AutoSchemaExtractor.

        Args:
            html_content: The HTML content to analyze

        Returns:
            A generated schema
        """
        try:
            # Parse HTML
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Initialize schema with empty fields list
            schema = {"fields": []}
            
            # Check for common product fields using known patterns
            for field_name, selectors in COMMON_SELECTORS.items():
                # Try each selector pattern
                for selector in selectors:
                    elements = soup.select(selector)
                    if elements:
                        # Found a matching element
                        field = {"name": field_name, "selector": selector}
                        
                        # Mark required fields
                        if field_name in ["title", "price"]:
                            field["required"] = True
                            
                        schema["fields"].append(field)
                        # Only keep the first successful selector for this field
                        break
            
            # If no fields were found for required elements, try fallback techniques
            if not any(f.get("name") == "title" for f in schema["fields"]):
                # Fallback for title: use first H1 tag
                h1 = soup.find("h1")
                if h1:
                    schema["fields"].append({
                        "name": "title",
                        "selector": "h1",
                        "required": True
                    })
            
            if not any(f.get("name") == "price" for f in schema["fields"]):
                # Fallback for price: look for elements with price-related text
                price_patterns = ["price", "amount", "cost", "$", "€", "£"]
                for pattern in price_patterns:
                    for element in soup.find_all(text=re.compile(pattern, re.IGNORECASE)):
                        parent = element.parent
                        if parent and parent.name in ["span", "div", "p"]:
                            selector = f"{parent.name}.{' '.join(parent.get('class', []))}"
                            if parent.get('id'):
                                selector = f"#{parent.get('id')}"
                            schema["fields"].append({
                                "name": "price",
                                "selector": selector,
                                "required": True
                            })
                            break
                    if any(f.get("name") == "price" for f in schema["fields"]):
                        break
            
            # Look for product images
            images = soup.find_all("img")
            for img in images:
                if ("product" in " ".join(img.get("class", [])).lower() or
                    "product" in img.get("id", "").lower() or
                    img.get("alt") and "product" in img.get("alt").lower()):
                    schema["fields"].append({
                        "name": "images",
                        "selector": f"img#{img.get('id')}" if img.get('id') else "img.product-image",
                        "attribute": "src"
                    })
                    break
            
            # Schema name and description
            schema["name"] = "Product Extraction Schema"
            schema["description"] = "Automatically generated schema for product extraction"
            
            return schema
        except Exception as e:
            logger.error(f"Error using auto schema generator: {e}")
            return {"fields": []}

    def analyze_schema_quality(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the quality of a schema and generate a report.

        Args:
            schema: The schema to analyze

        Returns:
            A report with quality metrics and suggestions
        """
        # Validate the schema first
        is_valid = self.validator.validate(schema)
        
        # Generate a report
        report = self.validator.generate_report()
        suggestions = {}
        
        if not is_valid:
            suggestions["corrections"] = self.validator.correct_schema(schema)
            
        # Add suggestions for improvements even if valid
        if os.getenv("APP_ENV") != "production":
            suggestions["improvements"] = self.validator.suggest_improvements(schema)
            
        return {
            "valid": is_valid,
            "report": report,
            "suggestions": suggestions
        }

    async def generate_and_validate(
        self, url: str, crawler: Optional[BaseCrawler] = None
    ) -> Dict[str, Any]:
        """
        Generate a schema for a URL and validate it, returning detailed results.

        Args:
            url: The URL to generate a schema for
            crawler: Optional crawler instance to use

        Returns:
            Results including the schema, validation status, and suggestions
        """
        schema, is_valid, errors = await self.generate_schema_from_url(url, crawler)
        
        result = {
            "url": url,
            "schema": schema,
            "valid": is_valid,
            "errors": errors,
        }
        
        if is_valid:
            quality_analysis = self.analyze_schema_quality(schema)
            result["quality_report"] = quality_analysis.get("report", {})
            result["suggestions"] = quality_analysis.get("suggestions", {})
        
        return result


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
