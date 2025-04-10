#!/usr/bin/env python
"""
Example demonstrating the use of different extraction methods in Crawl4AI.

This example shows how to use CSS selectors, XPath expressions, and hybrid
approaches for extracting product data from e-commerce websites.
"""

import asyncio
import logging
import os
import json
from pprint import pprint

from crawl4ai_llm.crawler.base import BaseCrawler
from crawl4ai_llm.crawler.content_filter import ContentFilter, CSSContentFilter, XPathContentFilter
from crawl4ai_llm.extraction import (
    CSSExtractor,
    XPathExtractor,
    HybridExtractor,
    ProductExtractor
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def extract_with_css(url):
    """Extract product data using CSS selectors."""
    logger.info("=== CSS Selector Extraction ===")
    
    # Create CSS selectors for product fields
    css_selectors = {
        "title": {
            "selector": "h1.product-title, .product-name, [itemprop='name']",
            "attribute": "text"
        },
        "price": {
            "selector": ".product-price, .price, [itemprop='price']",
            "attribute": "text"
        },
        "description": {
            "selector": ".product-description, [itemprop='description']",
            "attribute": "text"
        },
        "images_selector": ".product-image img, [itemprop='image']",
        "attributes_selector": ".product-attributes li, .product-specs tr",
        "attribute_name_selector": ".attribute-name, .spec-name, th",
        "attribute_value_selector": ".attribute-value, .spec-value, td",
    }
    
    # Optional content filter to focus on product section
    content_filter = ContentFilter(
        filter_type="css",
        selector=".product-container, .product-detail, [itemtype*='Product']",
        extract_text=False
    )
    
    # Create extractor and extract data
    css_extractor = CSSExtractor()
    result = await css_extractor.extract_with_css(
        url=url,
        selectors=css_selectors,
        content_filters=[content_filter]
    )
    
    logger.info(f"Extraction successful: {result.extraction_success}")
    return result


async def extract_with_xpath(url):
    """Extract product data using XPath expressions."""
    logger.info("=== XPath Expression Extraction ===")
    
    # Create XPath expressions for product fields
    xpath_expressions = {
        "title": {
            "xpath": "//h1 | //div[contains(@class, 'product-title')] | //*[@itemprop='name']"
        },
        "price": {
            "xpath": "//*[contains(@class, 'price')] | //*[@itemprop='price']"
        },
        "description": {
            "xpath": "//*[contains(@class, 'product-description')] | //*[@itemprop='description']"
        },
        "images_xpath": "//img[contains(@class, 'product-image')] | //*[@itemprop='image']",
        "attributes_xpath": "//ul[contains(@class, 'product-attributes')]/li | //table[contains(@class, 'product-specs')]/tr",
    }
    
    # Optional content filter to focus on product section
    content_filter = ContentFilter(
        filter_type="xpath",
        selector="//div[contains(@class, 'product-container')] | //*[@itemtype='http://schema.org/Product']",
        extract_text=False
    )
    
    # Create extractor and extract data
    xpath_extractor = XPathExtractor()
    result = await xpath_extractor.extract_with_xpath(
        url=url,
        xpath_expressions=xpath_expressions,
        content_filters=[content_filter]
    )
    
    logger.info(f"Extraction successful: {result.extraction_success}")
    return result


async def extract_with_hybrid(url):
    """Extract product data using a hybrid approach."""
    logger.info("=== Hybrid Extraction ===")
    
    # Create CSS selectors
    css_selectors = {
        "title": {
            "selector": "h1.product-title, .product-name, [itemprop='name']",
            "attribute": "text"
        },
        "price": {
            "selector": ".product-price, .price, [itemprop='price']",
            "attribute": "text"
        },
        "description": {
            "selector": ".product-description, [itemprop='description']",
            "attribute": "text"
        },
    }
    
    # Create XPath expressions
    xpath_expressions = {
        "brand": {
            "xpath": "//*[contains(@class, 'brand')] | //*[@itemprop='brand']"
        },
        "sku": {
            "xpath": "//*[contains(@class, 'sku')] | //*[@itemprop='sku']"
        },
        "images_xpath": "//img[contains(@class, 'product-image')] | //*[@itemprop='image']",
    }
    
    # Optional content filter to focus on product section
    content_filter = ContentFilter(
        filter_type="bm25",
        query="product details features price description specifications"
    )
    
    # Create hybrid extractor and extract data
    hybrid_extractor = HybridExtractor()
    result = await hybrid_extractor.extract_with_hybrid(
        url=url,
        css_selectors=css_selectors,
        xpath_expressions=xpath_expressions,
        use_auto_schema=True,  # Also use auto schema extraction
        use_fallback_llm=True,  # Use LLM extraction as fallback
        content_filters=[content_filter],
        extraction_order=["css", "xpath", "auto", "llm"],  # Try in this order
        merge_results=True  # Merge results from all successful strategies
    )
    
    logger.info(f"Extraction successful: {result.extraction_success}")
    return result


async def test_multiple_extraction_methods():
    """Test multiple extraction methods on a sample e-commerce product page."""
    # This is just a sample URL, replace with an actual product page
    product_url = "https://example.com/product/sample-product"
    
    logger.info(f"Testing extraction methods on {product_url}")
    
    try:
        # Extract with CSS selectors
        css_result = await extract_with_css(product_url)
        
        # Extract with XPath expressions
        xpath_result = await extract_with_xpath(product_url)
        
        # Extract with hybrid approach
        hybrid_result = await extract_with_hybrid(product_url)
        
        # Compare results
        logger.info("\n=== Extraction Results Comparison ===")
        
        # Print fields from each method
        logger.info("\nCSS Extraction - Title: " + css_result.title)
        logger.info("XPath Extraction - Title: " + xpath_result.title)
        logger.info("Hybrid Extraction - Title: " + hybrid_result.title)
        
        # Save results to JSON files for comparison
        os.makedirs("output", exist_ok=True)
        
        with open("output/css_extraction.json", "w") as f:
            json.dump(css_result.dict(), f, indent=2)
            
        with open("output/xpath_extraction.json", "w") as f:
            json.dump(xpath_result.dict(), f, indent=2)
            
        with open("output/hybrid_extraction.json", "w") as f:
            json.dump(hybrid_result.dict(), f, indent=2)
            
        logger.info("\nSaved full extraction results to output/*.json")
        
    except Exception as e:
        logger.error(f"Error during extraction: {str(e)}")


if __name__ == "__main__":
    # Run the example
    asyncio.run(test_multiple_extraction_methods()) 