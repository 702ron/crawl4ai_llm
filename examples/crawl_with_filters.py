#!/usr/bin/env python
"""
Example script showing how to use ContentFilter with BaseCrawler.

This example demonstrates how to crawl e-commerce product pages
with different content filtering strategies.
"""

import asyncio
import json
import logging
from pathlib import Path

from crawl4ai import CacheMode

from crawl4ai_llm.crawler import BaseCrawler, ContentFilter
from crawl4ai_llm.config import LLMConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def crawl_with_filters():
    """Demonstrate crawling with different content filters."""
    # URLs to crawl
    urls = [
        "https://www.amazon.com/PlayStation-5-Console-CFI-1000A-01/dp/B08FC5L3RG",
        "https://www.bestbuy.com/site/apple-airpods-pro-2nd-generation-white/4900964.p",
    ]
    
    # Example 1: Crawl with BM25 content filter
    logger.info("Crawling with BM25 content filter...")
    bm25_filter = ContentFilter(
        filter_type="bm25",
        query="product details specifications price",
        threshold=0.5
    )
    
    crawler = BaseCrawler(
        cache_mode=CacheMode.ENABLED,
        content_filters=[bm25_filter]
    )
    
    bm25_results = {}
    for url in urls:
        result = await crawler.crawl(url)
        bm25_results[url] = result
    
    # Example 2: Crawl with Pruning content filter
    logger.info("Crawling with Pruning content filter...")
    pruning_filter = ContentFilter(
        filter_type="pruning",
        threshold=0.4
    )
    
    crawler = BaseCrawler(
        cache_mode=CacheMode.ENABLED,
        content_filters=[pruning_filter]
    )
    
    pruning_results = {}
    for url in urls:
        result = await crawler.crawl(url)
        pruning_results[url] = result
    
    # Example 3: Crawl with LLM content filter (if API key is available)
    llm_results = {}
    try:
        logger.info("Crawling with LLM content filter...")
        # Use OpenAI as an example - replace with your actual key or environment variable
        llm_config = LLMConfig(
            provider="openai",
            api_token="YOUR_API_KEY_HERE",  # Replace with actual key or use from environment
            model="gpt-3.5-turbo"
        )
        
        llm_filter = ContentFilter(
            filter_type="llm",
            llm_config=llm_config,
            instruction="Extract the main product information, including name, price, features, and specifications."
        )
        
        crawler = BaseCrawler(
            cache_mode=CacheMode.ENABLED,
            content_filters=[llm_filter]
        )
        
        for url in urls:
            result = await crawler.crawl(url)
            llm_results[url] = result
            
    except Exception as e:
        logger.warning(f"Skipping LLM filter example: {str(e)}")
    
    # Save results to output directory
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / "bm25_results.json", "w") as f:
        # Serialize the results, handling non-serializable parts
        json.dump(bm25_results, f, indent=2, default=str)
    
    with open(output_dir / "pruning_results.json", "w") as f:
        json.dump(pruning_results, f, indent=2, default=str)
    
    if llm_results:
        with open(output_dir / "llm_results.json", "w") as f:
            json.dump(llm_results, f, indent=2, default=str)
    
    logger.info(f"Results saved to {output_dir.absolute()}")


if __name__ == "__main__":
    asyncio.run(crawl_with_filters()) 