#!/usr/bin/env python
"""
Content Filter Chain Example

This example demonstrates how to use ContentFilterChain to combine 
multiple content filters with different strategies.

The example shows:
1. Creating individual content filters
2. Creating filter chains with different strategies (ANY, ALL, SEQUENCE)
3. Applying filter chains to HTML content
4. Working with different filter types (BM25, regex, CSS, LLM)
"""

import asyncio
from typing import List, Dict, Optional, Union
import logging
from bs4 import BeautifulSoup

from crawl4ai_llm.crawler.content_filter import ContentFilter
from crawl4ai_llm.crawler.filter_chain import ContentFilterChain, FilterStrategy

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("filter-chain-example")

# Sample HTML for testing filters
SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Sample Product Page</title>
</head>
<body>
    <div class="product-container">
        <h1 class="product-title">Premium Bluetooth Headphones</h1>
        <div class="product-price">$129.99</div>
        <div class="product-description">
            <p>Experience premium sound quality with our wireless Bluetooth headphones.</p>
            <p>Features include:</p>
            <ul>
                <li>40 hours of battery life</li>
                <li>Active noise cancellation</li>
                <li>High-fidelity sound</li>
                <li>Comfortable over-ear design</li>
            </ul>
        </div>
        <div class="reviews">
            <div class="review">
                <div class="review-rating">★★★★★</div>
                <div class="review-text">Best headphones I've ever owned!</div>
            </div>
            <div class="review">
                <div class="review-rating">★★★★☆</div>
                <div class="review-text">Great sound, but a bit expensive.</div>
            </div>
        </div>
        <div class="related-products">
            <h3>You might also like:</h3>
            <ul>
                <li>Wireless Earbuds - $89.99</li>
                <li>Headphone Stand - $24.99</li>
                <li>Replacement Ear Pads - $19.99</li>
            </ul>
        </div>
    </div>
</body>
</html>
"""

async def create_basic_filters():
    """Create and demonstrate basic individual filters"""
    logger.info("Creating basic content filters...")
    
    # BM25 Filter - for keyword-based filtering
    bm25_filter = ContentFilter(
        filter_type="bm25",
        query="wireless bluetooth headphones noise cancellation"
    )
    
    # CSS Selector Filter - for structure-based filtering
    css_filter = ContentFilter(
        filter_type="css",
        query=".product-description, .product-title, .product-price"
    )
    
    # Regex Filter - for pattern-based filtering
    regex_filter = ContentFilter(
        filter_type="regex",
        query=r"\$\d+\.\d{2}"  # Match price format $XX.XX
    )
    
    # Apply each filter separately
    bm25_results = await bm25_filter.filter_content(SAMPLE_HTML)
    css_results = await css_filter.filter_content(SAMPLE_HTML)
    regex_results = await regex_filter.filter_content(SAMPLE_HTML)
    
    logger.info(f"BM25 filter found {len(bm25_results)} results")
    logger.info(f"CSS filter found {len(css_results)} results")
    logger.info(f"Regex filter found {len(regex_results)} results")
    
    if bm25_results:
        logger.info(f"Sample BM25 result: {bm25_results[0][:100]}...")
    if css_results:
        logger.info(f"Sample CSS result: {css_results[0][:100]}...")
    if regex_results:
        logger.info(f"Sample Regex result: {regex_results[0]}")
    
    return bm25_filter, css_filter, regex_filter

async def demonstrate_filter_chain_strategies(filters):
    """Demonstrate different filter chain strategies"""
    bm25_filter, css_filter, regex_filter = filters
    
    logger.info("\nDemonstrating filter chain strategies...")
    
    # 1. SEQUENCE strategy - Apply filters in sequence
    sequence_chain = ContentFilterChain(
        filters=[bm25_filter, css_filter],
        strategy=FilterStrategy.SEQUENCE
    )
    logger.info(f"Created SEQUENCE filter chain: {sequence_chain}")
    
    sequence_results = await sequence_chain.filter_content(SAMPLE_HTML)
    logger.info(f"SEQUENCE strategy found {len(sequence_results)} results")
    for i, result in enumerate(sequence_results[:2]):
        logger.info(f"SEQUENCE result {i+1}: {result[:100]}...")
    
    # 2. ALL strategy - Content must pass all filters
    all_chain = ContentFilterChain(
        filters=[css_filter, regex_filter],
        strategy=FilterStrategy.ALL
    )
    logger.info(f"Created ALL filter chain: {all_chain}")
    
    all_results = await all_chain.filter_content(SAMPLE_HTML)
    logger.info(f"ALL strategy found {len(all_results)} results")
    for i, result in enumerate(all_results[:2]):
        logger.info(f"ALL result {i+1}: {result[:100]}...")
    
    # 3. ANY strategy - Content must pass at least one filter
    any_chain = ContentFilterChain(
        filters=[bm25_filter, regex_filter],
        strategy=FilterStrategy.ANY
    )
    logger.info(f"Created ANY filter chain: {any_chain}")
    
    any_results = await any_chain.filter_content(SAMPLE_HTML)
    logger.info(f"ANY strategy found {len(any_results)} results")
    for i, result in enumerate(any_results[:2]):
        logger.info(f"ANY result {i+1}: {result[:100]}...")
    
    return sequence_chain, all_chain, any_chain

async def demonstrate_nested_chains(basic_chains):
    """Demonstrate nested filter chains"""
    sequence_chain, all_chain, any_chain = basic_chains
    
    logger.info("\nDemonstrating nested filter chains...")
    
    # Create a regex filter for finding review content
    review_filter = ContentFilter(
        filter_type="regex",
        query=r"★{3,5}"  # Find reviews with 3+ stars
    )
    
    # Create a nested chain
    nested_chain = ContentFilterChain(
        filters=[
            sequence_chain,  # Use the sequence chain from before
            review_filter,   # Add the review filter
        ],
        strategy=FilterStrategy.ALL  # Both filters must pass
    )
    
    logger.info(f"Created nested filter chain: {nested_chain}")
    
    nested_results = await nested_chain.filter_content(SAMPLE_HTML)
    logger.info(f"Nested chain found {len(nested_results)} results")
    for i, result in enumerate(nested_results[:2]):
        logger.info(f"Nested chain result {i+1}: {result[:100]}...")
    
    # Create an even more complex chain
    complex_chain = ContentFilterChain(
        filters=[
            all_chain,      # Use the ALL chain from before
            any_chain,      # Use the ANY chain from before
            nested_chain    # Use the nested chain we just created
        ],
        strategy=FilterStrategy.ANY  # Any of these chains can pass
    )
    
    logger.info(f"Created complex filter chain: {complex_chain}")
    
    complex_results = await complex_chain.filter_content(SAMPLE_HTML)
    logger.info(f"Complex chain found {len(complex_results)} results")
    
    return nested_chain, complex_chain

async def practical_example():
    """A practical example for a real-world scenario"""
    logger.info("\nPractical example: Product information extraction")
    
    # Create specialized filters for different aspects of a product
    title_filter = ContentFilter(
        filter_type="css",
        query=".product-title, h1"  # Extract product titles
    )
    
    price_filter = ContentFilter(
        filter_type="regex",
        query=r"\$\d+\.\d{2}"  # Extract price information
    )
    
    description_filter = ContentFilter(
        filter_type="css",
        query=".product-description"  # Extract product descriptions
    )
    
    review_filter = ContentFilter(
        filter_type="css",
        query=".review"  # Extract product reviews
    )
    
    # Create a filter chain for essential product info
    essential_info_chain = ContentFilterChain(
        filters=[title_filter, price_filter],
        strategy=FilterStrategy.ALL  # Must have both title and price
    )
    
    # Create a chain for additional product details
    details_chain = ContentFilterChain(
        filters=[description_filter, review_filter],
        strategy=FilterStrategy.ANY  # Either description or reviews is fine
    )
    
    # Create the complete extraction chain
    extraction_chain = ContentFilterChain(
        filters=[essential_info_chain, details_chain],
        strategy=FilterStrategy.SEQUENCE  # First get essential info, then details
    )
    
    logger.info(f"Created product extraction chain: {extraction_chain}")
    
    # Apply the chain
    extracted_content = await extraction_chain.filter_content(SAMPLE_HTML)
    
    # Process and display results
    logger.info(f"Extracted {len(extracted_content)} content pieces")
    
    # Parse the results into a structured format
    product_data = {
        "title": None,
        "price": None,
        "description": None,
        "reviews": []
    }
    
    for content in extracted_content:
        # Try to parse as HTML
        try:
            soup = BeautifulSoup(content, "html.parser")
            
            # Look for product title
            title_elem = soup.select_one(".product-title, h1")
            if title_elem and not product_data["title"]:
                product_data["title"] = title_elem.text.strip()
            
            # Look for product price
            price_elem = soup.select_one(".product-price")
            if price_elem and not product_data["price"]:
                product_data["price"] = price_elem.text.strip()
            
            # Look for product description
            desc_elem = soup.select_one(".product-description")
            if desc_elem and not product_data["description"]:
                product_data["description"] = desc_elem.text.strip()
            
            # Look for reviews
            review_elems = soup.select(".review")
            for review in review_elems:
                rating = review.select_one(".review-rating")
                text = review.select_one(".review-text")
                if rating and text:
                    product_data["reviews"].append({
                        "rating": rating.text.strip(),
                        "text": text.text.strip()
                    })
        
        except Exception as e:
            # If not valid HTML, check if it's a price
            if not product_data["price"] and "$" in content:
                product_data["price"] = content.strip()
    
    # Display the structured product data
    logger.info("Extracted product data:")
    logger.info(f"Title: {product_data['title']}")
    logger.info(f"Price: {product_data['price']}")
    logger.info(f"Description: {product_data['description'][:100]}..." if product_data["description"] else "No description found")
    logger.info(f"Reviews: {len(product_data['reviews'])} found")
    for i, review in enumerate(product_data["reviews"]):
        logger.info(f"  Review {i+1}: {review['rating']} - {review['text']}")
    
    return extraction_chain, product_data

async def main():
    """Run all filter chain examples"""
    logger.info("Starting content filter chain examples")
    
    try:
        # Create and test basic filters
        basic_filters = await create_basic_filters()
        
        # Demonstrate chain strategies
        basic_chains = await demonstrate_filter_chain_strategies(basic_filters)
        
        # Demonstrate nested chains
        nested_chains = await demonstrate_nested_chains(basic_chains)
        
        # Practical example
        extraction_chain, product_data = await practical_example()
        
        logger.info("\nAll filter chain examples completed successfully")
        
    except Exception as e:
        logger.error(f"Error in examples: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main()) 