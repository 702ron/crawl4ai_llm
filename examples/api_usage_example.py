#!/usr/bin/env python
"""
Example script demonstrating direct API usage of the crawl4ai_llm package.

This script shows how to use the ProductExtractor and other components
directly in your Python code without using the CLI.
"""

import asyncio
import json
from typing import Dict, Any, Optional

from crawl4ai_llm.extraction import ProductExtractor
from crawl4ai_llm.models import ProductData
from crawl4ai_llm.crawler import ContentFilter, ContentFilterChain


async def extract_with_auto_schema(url: str) -> Optional[Dict[str, Any]]:
    """
    Extract product data using auto schema generation.
    
    Args:
        url: The URL of the product page
        
    Returns:
        Extracted product data as a dictionary or None if extraction failed
    """
    extractor = ProductExtractor(headless=True)
    result = await extractor.extract_with_auto_schema(url)
    
    if result:
        # Convert to dictionary for serialization
        return result.dict()
    return None


async def extract_with_custom_filter(url: str) -> Optional[Dict[str, Any]]:
    """
    Extract product data using a custom content filter chain.
    
    Args:
        url: The URL of the product page
        
    Returns:
        Extracted product data as a dictionary or None if extraction failed
    """
    # Create content filters to target specific parts of the page
    title_filter = ContentFilter(filter_type="bm25", query="product title")
    price_filter = ContentFilter(filter_type="bm25", query="product price")
    description_filter = ContentFilter(filter_type="bm25", query="product description")
    
    # Combine filters into a chain
    filter_chain = ContentFilterChain(
        filters=[title_filter, price_filter, description_filter],
        strategy="ALL"
    )
    
    extractor = ProductExtractor(headless=True, content_filters=filter_chain)
    result = await extractor.extract_with_auto_schema(url)
    
    if result:
        return result.dict()
    return None


async def extract_with_llm(url: str, api_key: str) -> Optional[Dict[str, Any]]:
    """
    Extract product data using LLM-based extraction.
    
    Args:
        url: The URL of the product page
        api_key: OpenAI API key
        
    Returns:
        Extracted product data as a dictionary or None if extraction failed
    """
    extractor = ProductExtractor(
        headless=True,
        llm_config={"api_key": api_key, "model": "gpt-3.5-turbo"}
    )
    result = await extractor.extract_with_llm(url)
    
    if result:
        return result.dict()
    return None


async def main():
    """
    Run examples of different extraction methods.
    """
    # Replace with your product URL and API key
    url = "https://www.amazon.com/dp/B08F7CJQZ3"
    api_key = "your-openai-api-key"  # Replace with your actual API key
    
    print("Extracting with auto schema generation...")
    result = await extract_with_auto_schema(url)
    if result:
        print(json.dumps(result, indent=2))
    else:
        print("Auto schema extraction failed")
    
    print("\nExtracting with custom filter chain...")
    result = await extract_with_custom_filter(url)
    if result:
        print(json.dumps(result, indent=2))
    else:
        print("Custom filter extraction failed")
    
    # Uncomment to use LLM-based extraction
    # print("\nExtracting with LLM...")
    # result = await extract_with_llm(url, api_key)
    # if result:
    #     print(json.dumps(result, indent=2))
    # else:
    #     print("LLM extraction failed")


if __name__ == "__main__":
    asyncio.run(main()) 