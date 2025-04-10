#!/usr/bin/env python
"""
Example script demonstrating advanced content filtering techniques.

This example shows how to use different content filter types and chain strategies
to effectively extract product data from e-commerce websites.
"""

import asyncio
import json
import sys
import os
from typing import Dict, List, Any, Optional

# Add parent directory to path to import from crawl4ai_llm
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawl4ai_llm.crawler import BaseCrawler, ContentFilter, ContentFilterChain
from crawl4ai_llm.extraction import ProductExtractor


async def demo_single_filters(url: str) -> None:
    """
    Demonstrate the effect of individual content filters.
    
    Args:
        url: The URL of the product page to crawl
    """
    print("\n=== Demonstrating Individual Filters ===\n")
    
    # BM25 Filter (keyword-based relevance)
    bm25_filter = ContentFilter(
        filter_type="bm25", 
        query="product price features description specifications",
        threshold=0.3
    )
    crawler_bm25 = BaseCrawler(content_filters=bm25_filter)
    result_bm25 = await crawler_bm25.crawl(url)
    print(f"BM25 Filter - Found {len(result_bm25.extracted_content)} content blocks")
    
    # Pruning Filter (structural analysis)
    pruning_filter = ContentFilter(
        filter_type="pruning",
        threshold=0.4
    )
    crawler_pruning = BaseCrawler(content_filters=pruning_filter)
    result_pruning = await crawler_pruning.crawl(url)
    print(f"Pruning Filter - Found {len(result_pruning.extracted_content)} content blocks")
    
    # CSS Filter (DOM-based)
    css_filter = ContentFilter(
        filter_type="css",
        selector="#productTitle, #priceblock_ourprice, .a-price, #feature-bullets, #productDescription",
        extract_text=True
    )
    crawler_css = BaseCrawler(content_filters=css_filter)
    result_css = await crawler_css.crawl(url)
    print(f"CSS Filter - Found {len(result_css.extracted_content)} content blocks")
    
    # Regex Filter (pattern-based)
    regex_filter = ContentFilter(
        filter_type="regex",
        pattern=r"\$(\d+(?:\.\d{2})?)",
    )
    crawler_regex = BaseCrawler(content_filters=regex_filter)
    result_regex = await crawler_regex.crawl(url)
    print(f"Regex Filter - Found {len(result_regex.extracted_content)} content blocks")
    
    # Sample output from each filter
    if result_bm25.extracted_content:
        print("\nBM25 Filter Sample:")
        print(result_bm25.extracted_content[0][:200] + "...")
    
    if result_css.extracted_content:
        print("\nCSS Filter Sample:")
        for content in result_css.extracted_content[:2]:
            print(content[:100] + "...")
    
    if result_regex.extracted_content:
        print("\nRegex Filter Sample (Price matches):")
        print(result_regex.extracted_content[:5])


async def demo_filter_chains(url: str) -> Dict[str, Any]:
    """
    Demonstrate different filter chain strategies.
    
    Args:
        url: The URL of the product page to crawl
        
    Returns:
        Dictionary with results from different chain strategies
    """
    print("\n=== Demonstrating Filter Chains ===\n")
    
    # Create individual filters
    title_filter = ContentFilter(filter_type="css", selector=".product-title, #productTitle, .pdp-title", extract_text=True)
    price_filter = ContentFilter(filter_type="css", selector=".product-price, #priceblock_ourprice, .a-price", extract_text=True)
    price_regex = ContentFilter(filter_type="regex", pattern=r"\$(\d+(?:\.\d{2})?)")
    desc_filter = ContentFilter(filter_type="css", selector=".product-description, #feature-bullets, #productDescription", extract_text=True)
    desc_bm25 = ContentFilter(filter_type="bm25", query="product description features specifications", threshold=0.4)
    
    # Create filter chains with different strategies
    sequence_chain = ContentFilterChain(
        filters=[title_filter, price_filter, desc_filter],
        strategy="SEQUENCE"
    )
    
    all_chain = ContentFilterChain(
        filters=[title_filter, price_filter, desc_filter],
        strategy="ALL"
    )
    
    any_chain = ContentFilterChain(
        filters=[title_filter, price_filter, desc_filter],
        strategy="ANY"
    )
    
    # Mixed chain (combining different filter types)
    mixed_chain = ContentFilterChain(
        filters=[title_filter, price_regex, desc_bm25],
        strategy="ALL"
    )
    
    # Nested chain (chain inside another chain)
    price_chain = ContentFilterChain(
        filters=[price_filter, price_regex],
        strategy="ANY"
    )
    
    nested_chain = ContentFilterChain(
        filters=[title_filter, price_chain, desc_filter],
        strategy="ALL"
    )
    
    # Run crawlers with different chains
    crawler_sequence = BaseCrawler(content_filters=sequence_chain)
    result_sequence = await crawler_sequence.crawl(url)
    
    crawler_all = BaseCrawler(content_filters=all_chain)
    result_all = await crawler_all.crawl(url)
    
    crawler_any = BaseCrawler(content_filters=any_chain)
    result_any = await crawler_any.crawl(url)
    
    crawler_mixed = BaseCrawler(content_filters=mixed_chain)
    result_mixed = await crawler_mixed.crawl(url)
    
    crawler_nested = BaseCrawler(content_filters=nested_chain)
    result_nested = await crawler_nested.crawl(url)
    
    # Print results
    print(f"SEQUENCE Strategy - Found {len(result_sequence.extracted_content)} content blocks")
    print(f"ALL Strategy - Found {len(result_all.extracted_content)} content blocks")
    print(f"ANY Strategy - Found {len(result_any.extracted_content)} content blocks")
    print(f"Mixed Filter Types - Found {len(result_mixed.extracted_content)} content blocks")
    print(f"Nested Chains - Found {len(result_nested.extracted_content)} content blocks")
    
    return {
        "SEQUENCE": result_sequence.extracted_content,
        "ALL": result_all.extracted_content,
        "ANY": result_any.extracted_content,
        "MIXED": result_mixed.extracted_content,
        "NESTED": result_nested.extracted_content
    }


async def extract_with_optimized_filters(url: str) -> Optional[Dict[str, Any]]:
    """
    Extract product data with optimized content filters.
    
    Args:
        url: The URL of the product page
        
    Returns:
        Extracted product data as a dictionary or None if extraction failed
    """
    print("\n=== Extracting with Optimized Filters ===\n")
    
    # Create optimized filter chain for better extraction quality
    # First apply pruning to remove boilerplate content
    pruning_filter = ContentFilter(filter_type="pruning", threshold=0.5)
    
    # Then extract specific elements with CSS selectors
    title_filter = ContentFilter(filter_type="css", selector="h1, .product-title, #productTitle", extract_text=True)
    price_filter = ContentFilter(filter_type="css", selector=".price, .product-price, #priceblock_ourprice, .a-price", extract_text=True)
    desc_filter = ContentFilter(filter_type="css", selector=".description, #productDescription, #feature-bullets", extract_text=True)
    specs_filter = ContentFilter(filter_type="css", selector=".specs, .product-specs, .techD", extract_text=True)
    
    # Use BM25 as a fallback for more general content matching
    bm25_filter = ContentFilter(filter_type="bm25", query="product specifications features technical details", threshold=0.4)
    
    # Create a nested chain structure
    main_content_chain = ContentFilterChain(
        filters=[
            title_filter,
            price_filter,
            ContentFilterChain(
                filters=[desc_filter, bm25_filter],
                strategy="ANY"  # Use either specific CSS or BM25 for description
            ),
            specs_filter
        ],
        strategy="ALL"  # Need all these elements for a complete product
    )
    
    # The complete filter chain first prunes, then extracts main content
    complete_chain = ContentFilterChain(
        filters=[pruning_filter, main_content_chain],
        strategy="SEQUENCE"  # Apply pruning first, then extract main content
    )
    
    # Create extractor with optimized filters
    extractor = ProductExtractor(headless=True, content_filters=complete_chain)
    
    # Extract product data using auto schema
    result = await extractor.extract_with_auto_schema(url)
    
    if result:
        print("Successfully extracted product data:")
        print(f"Title: {result.title}")
        if result.price:
            print(f"Price: {result.price.current} {result.price.currency}")
        print(f"Description length: {len(result.description) if result.description else 0} chars")
        print(f"Number of images: {len(result.images) if result.images else 0}")
        return result.dict()
    
    print("Failed to extract product data")
    return None


async def main():
    """Main function to run the demos."""
    # Default URL (an Amazon product page)
    default_url = "https://www.amazon.com/dp/B08F7CJQZ3"
    
    # Get URL from command line argument or use default
    url = sys.argv[1] if len(sys.argv) > 1 else default_url
    print(f"Using URL: {url}")
    
    # Demo single filters
    await demo_single_filters(url)
    
    # Demo filter chains
    chain_results = await demo_filter_chains(url)
    
    # Show sample from each chain
    for strategy, content in chain_results.items():
        if content:
            print(f"\n{strategy} Strategy Sample:")
            sample = content[0] if len(content[0]) < 100 else content[0][:100] + "..."
            print(sample)
    
    # Extract with optimized filters
    product_data = await extract_with_optimized_filters(url)
    
    if product_data:
        # Save the extracted data to a file
        output_file = "extracted_product.json"
        with open(output_file, "w") as f:
            json.dump(product_data, f, indent=2)
        print(f"\nExtracted product data saved to {output_file}")


if __name__ == "__main__":
    asyncio.run(main()) 