#!/usr/bin/env python
"""
Example script for batch extraction of product data from multiple URLs.
"""

import argparse
import asyncio
import csv
import json
import os
import sys
from typing import Dict, List, Optional, Union

# Add parent directory to path to import from crawl4ai_llm
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawl4ai_llm.extraction.product_extractor import ProductExtractor
from crawl4ai_llm.models import ProductData


async def extract_product(url: str, extractor: ProductExtractor, method: str = "auto_schema") -> Optional[ProductData]:
    """
    Extract product data from a URL using the specified method.
    
    Args:
        url: Product URL to extract from
        extractor: ProductExtractor instance
        method: Extraction method ("auto_schema", "llm", or "auto")
        
    Returns:
        ProductData object or None if extraction failed
    """
    print(f"Extracting data from: {url}")
    try:
        if method == "auto_schema":
            result = await extractor.extract_with_auto_schema(url)
        elif method == "llm":
            result = await extractor.extract_with_llm(url)
        else:  # auto
            result = await extractor.extract(url)
        return result
    except Exception as e:
        print(f"Error extracting data from {url}: {e}")
        return None


async def batch_extract(
    urls: List[str], 
    output_file: str, 
    format: str = "json", 
    method: str = "auto", 
    concurrency: int = 3,
    api_key: Optional[str] = None
) -> None:
    """
    Extract product data from multiple URLs concurrently.
    
    Args:
        urls: List of product URLs
        output_file: Path to output file
        format: Output format ("json" or "csv")
        method: Extraction method ("auto_schema", "llm", or "auto")
        concurrency: Maximum number of concurrent extractions
        api_key: API key for the extractor
    """
    if api_key:
        os.environ["CRAWL4AI_API_KEY"] = api_key
    elif "CRAWL4AI_API_KEY" not in os.environ:
        print("Warning: CRAWL4AI_API_KEY environment variable not set. Extraction may fail.")

    extractor = ProductExtractor()
    semaphore = asyncio.Semaphore(concurrency)
    
    async def extract_with_semaphore(url):
        async with semaphore:
            return await extract_product(url, extractor, method)
    
    tasks = [extract_with_semaphore(url) for url in urls]
    results = await asyncio.gather(*tasks)
    results = [r for r in results if r is not None]
    
    # Save results
    if format.lower() == "json":
        with open(output_file, "w") as f:
            json.dump([r.dict() for r in results], f, indent=2)
    elif format.lower() == "csv":
        if not results:
            print("No results to save")
            return
            
        # Flatten the first result to get all possible fields
        first_result = results[0].dict()
        headers = flatten_dict(first_result).keys()
        
        with open(output_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for result in results:
                flat_result = flatten_dict(result.dict())
                writer.writerow(flat_result)
    
    print(f"Extracted {len(results)} products out of {len(urls)} URLs")
    print(f"Results saved to {output_file}")


def flatten_dict(d: Dict, parent_key: str = "", sep: str = "_") -> Dict:
    """Flatten a nested dictionary"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep).items())
        elif isinstance(v, list):
            # For simplicity, just take the first item in lists or join strings
            if v and isinstance(v[0], dict):
                items.extend(flatten_dict(v[0], new_key, sep).items())
            else:
                items.append((new_key, ", ".join(str(x) for x in v)))
        else:
            items.append((new_key, v))
    return dict(items)


def read_urls(file_path: str) -> List[str]:
    """Read URLs from a file, one per line"""
    with open(file_path, "r") as f:
        urls = [line.strip() for line in f if line.strip()]
    return urls


def parse_args():
    parser = argparse.ArgumentParser(description="Batch extract product data from URLs")
    parser.add_argument("-i", "--input", required=True, help="Input file with URLs (one per line)")
    parser.add_argument("-o", "--output", required=True, help="Output file path")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format (default: json)")
    parser.add_argument("--method", choices=["auto_schema", "llm", "auto"], default="auto", 
                        help="Extraction method (default: auto)")
    parser.add_argument("--concurrency", type=int, default=3, 
                        help="Maximum number of concurrent extractions (default: 3)")
    parser.add_argument("--api-key", help="API key (overrides environment variable)")
    return parser.parse_args()


async def main():
    args = parse_args()
    urls = read_urls(args.input)
    print(f"Loaded {len(urls)} URLs from {args.input}")
    await batch_extract(
        urls=urls,
        output_file=args.output,
        format=args.format,
        method=args.method,
        concurrency=args.concurrency,
        api_key=args.api_key
    )


if __name__ == "__main__":
    asyncio.run(main()) 