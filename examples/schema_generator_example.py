#!/usr/bin/env python
"""
Example script demonstrating schema generation and validation.

This example shows how to generate extraction schemas for e-commerce websites
and validate them to ensure they can extract necessary product information.
"""

import asyncio
import json
import sys
import os
import argparse
from typing import Dict, Any, Optional

# Add parent directory to path to import from crawl4ai_llm
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawl4ai_llm.crawler import BaseCrawler
from crawl4ai_llm.extraction import SchemaGenerator, SchemaValidator


async def generate_schema(url: str, save_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate an extraction schema for a product page.
    
    Args:
        url: The URL of the product page
        save_path: Optional path to save the generated schema
        
    Returns:
        The generated schema
    """
    print(f"Generating schema for: {url}")
    
    # Create a crawler and get the HTML content
    crawler = BaseCrawler()
    result = await crawler.crawl(url)
    
    if not result.html:
        print("Error: Failed to retrieve HTML content")
        sys.exit(1)
    
    # Create a schema generator and generate a schema
    generator = SchemaGenerator()
    schema = await generator.generate_schema(result.html, url)
    
    print("\nGenerated Schema:")
    print(json.dumps(schema, indent=2))
    
    # Validate the schema
    validator = SchemaValidator()
    validation_result = validator.validate_schema(schema)
    
    if validation_result:
        print("\n✅ Schema is valid!")
    else:
        print("\n❌ Schema is invalid. Correcting issues...")
        # Auto-correct schema issues
        corrected_schema = validator.correct_schema(schema)
        schema = corrected_schema
        print("\nCorrected Schema:")
        print(json.dumps(schema, indent=2))
    
    # Generate a quality report
    quality_report = validator.generate_quality_report(schema)
    print("\nSchema Quality Report:")
    print(json.dumps(quality_report, indent=2))
    
    # Save the schema if a path is provided
    if save_path:
        with open(save_path, "w") as f:
            json.dump(schema, f, indent=2)
        print(f"\nSchema saved to: {save_path}")
    
    return schema


async def test_schema_extraction(url: str, schema: Dict[str, Any]) -> None:
    """
    Test a schema by attempting to extract product data.
    
    Args:
        url: The URL of the product page
        schema: The extraction schema to test
    """
    from crawl4ai_llm.extraction import ProductExtractor
    
    print(f"\nTesting schema extraction on: {url}")
    
    # Create an extractor
    extractor = ProductExtractor(headless=True)
    
    # Extract with the provided schema
    result = await extractor.extract_with_schema(url, schema)
    
    if result:
        print("\n✅ Extraction successful!")
        print(f"Title: {result.title}")
        if result.price:
            print(f"Price: {result.price.current} {result.price.currency}")
        print(f"Description length: {len(result.description) if result.description else 0} chars")
        print(f"Number of images: {len(result.images) if result.images else 0}")
        
        # Save the extracted data
        output_file = "extracted_product_test.json"
        with open(output_file, "w") as f:
            json.dump(result.dict(), f, indent=2)
        print(f"\nExtracted product data saved to {output_file}")
    else:
        print("\n❌ Extraction failed")


async def compare_with_auto_schema(url: str) -> None:
    """
    Compare generated schema with auto schema extraction.
    
    Args:
        url: The URL of the product page
    """
    from crawl4ai_llm.extraction import ProductExtractor
    
    print(f"\nComparing with auto schema extraction: {url}")
    
    # Create an extractor
    extractor = ProductExtractor(headless=True)
    
    # Extract with auto schema
    result = await extractor.extract_with_auto_schema(url)
    
    if result:
        print("\n✅ Auto schema extraction successful!")
        print(f"Title: {result.title}")
        if result.price:
            print(f"Price: {result.price.current} {result.price.currency}")
        print(f"Description length: {len(result.description) if result.description else 0} chars")
        print(f"Number of images: {len(result.images) if result.images else 0}")
        
        # Save the auto-extracted data
        output_file = "auto_extracted_product.json"
        with open(output_file, "w") as f:
            json.dump(result.dict(), f, indent=2)
        print(f"\nAuto-extracted product data saved to {output_file}")
    else:
        print("\n❌ Auto schema extraction failed")


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Schema Generator Example")
    parser.add_argument("url", nargs="?", help="URL of the product page")
    parser.add_argument(
        "--save", help="Path to save the generated schema", default="generated_schema.json"
    )
    parser.add_argument(
        "--test", action="store_true", help="Test the schema with extraction"
    )
    parser.add_argument(
        "--compare", action="store_true", help="Compare with auto schema extraction"
    )
    parser.add_argument(
        "--schema", help="Path to an existing schema file to test (skips generation)"
    )
    return parser.parse_args()


async def main():
    """Main function."""
    args = parse_args()
    
    # Default URL if none provided
    url = args.url or "https://www.amazon.com/dp/B08F7CJQZ3"
    
    schema = None
    
    # Load existing schema if provided
    if args.schema:
        try:
            with open(args.schema, "r") as f:
                schema = json.load(f)
            print(f"Loaded schema from: {args.schema}")
        except Exception as e:
            print(f"Error loading schema: {e}")
            sys.exit(1)
    else:
        # Generate a new schema
        schema = await generate_schema(url, args.save)
    
    # Test the schema if requested
    if args.test and schema:
        await test_schema_extraction(url, schema)
    
    # Compare with auto schema if requested
    if args.compare:
        await compare_with_auto_schema(url)


if __name__ == "__main__":
    asyncio.run(main()) 