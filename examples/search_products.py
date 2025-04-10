#!/usr/bin/env python
"""
Example script for searching and displaying products from storage.

This script allows you to:
1. List all stored products
2. Filter products by various criteria
3. Sort products by different fields
4. Display product details in various formats
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from tabulate import tabulate

from crawl4ai_llm.config import StorageConfig
from crawl4ai_llm.models.product import ProductData
from crawl4ai_llm.storage.factory import get_storage


def format_product_summary(product: ProductData) -> Dict[str, Any]:
    """Create a summary of product data for display."""
    return {
        "id": product.id,
        "title": (
            (product.title[:40] + "...") if len(product.title) > 40 else product.title
        ),
        "price": (
            f"{product.price.amount} {product.price.currency}"
            if product.price
            else "N/A"
        ),
        "brand": product.brand or "N/A",
        "available": "Yes" if product.available else "No",
        "images": len(product.images) if product.images else 0,
        "date_extracted": (
            product.date_extracted.strftime("%Y-%m-%d %H:%M:%S")
            if product.date_extracted
            else "N/A"
        ),
    }


def search_products(
    storage_path: str,
    query: Optional[str] = None,
    sort_by: Optional[str] = None,
    available_only: bool = False,
    limit: int = 10,
    format_type: str = "table",
    product_id: Optional[str] = None,
) -> None:
    """
    Search products and display results.

    Args:
        storage_path: Path to storage directory
        query: Optional text query to filter products
        sort_by: Field to sort results by
        available_only: Only show products marked as available
        limit: Maximum number of products to display
        format_type: Output format (table, json, detailed)
        product_id: Specific product ID to display
    """
    # Create storage configuration
    storage_config = StorageConfig(type="json", path=storage_path, use_uuid=True)

    # Get storage instance
    try:
        storage = get_storage(storage_config)
    except Exception as e:
        print(f"Error initializing storage: {str(e)}")
        sys.exit(1)

    # Display a specific product if ID is provided
    if product_id:
        try:
            product = storage.get_product(product_id)
            if not product:
                print(f"Product with ID {product_id} not found.")
                sys.exit(1)

            if format_type == "json":
                print(json.dumps(product.dict(), indent=2, default=str))
            else:
                # Detailed view with all product information
                print(f"\n=== Product: {product.title} ===\n")
                print(f"ID: {product.id}")
                print(f"URL: {product.url}")
                print(f"Brand: {product.brand or 'N/A'}")

                if product.price:
                    print(f"Price: {product.price.amount} {product.price.currency}")
                else:
                    print("Price: N/A")

                print(f"Available: {'Yes' if product.available else 'No'}")

                if product.description:
                    print(f"\nDescription:\n{product.description[:200]}...")

                if product.attributes:
                    print("\nAttributes:")
                    for key, value in product.attributes.items():
                        print(f"  - {key}: {value}")

                if product.images:
                    print(f"\nImages ({len(product.images)}):")
                    for i, img in enumerate(product.images[:5]):
                        print(f"  {i+1}. {img.url}")
                    if len(product.images) > 5:
                        print(f"  ... and {len(product.images) - 5} more")

                if product.variants:
                    print(f"\nVariants ({len(product.variants)}):")
                    for i, variant in enumerate(product.variants[:5]):
                        price_str = (
                            f"{variant.price.amount} {variant.price.currency}"
                            if variant.price
                            else "N/A"
                        )
                        print(f"  {i+1}. {variant.name} - {price_str}")
                    if len(product.variants) > 5:
                        print(f"  ... and {len(product.variants) - 5} more")

                print(
                    f"\nExtracted: {product.date_extracted.strftime('%Y-%m-%d %H:%M:%S') if product.date_extracted else 'N/A'}"
                )

            return
        except Exception as e:
            print(f"Error retrieving product: {str(e)}")
            sys.exit(1)

    # List products with optional filtering
    try:
        filters = {}
        if query:
            filters["text"] = query
        if available_only:
            filters["available"] = True

        products = storage.list_products(filters=filters, sort_by=sort_by, limit=limit)

        if not products:
            print("No products found matching your criteria.")
            return

        if format_type == "json":
            # JSON output
            output = [format_product_summary(p) for p in products]
            print(json.dumps(output, indent=2))
        elif format_type == "table":
            # Table output
            headers = [
                "ID",
                "Title",
                "Price",
                "Brand",
                "Available",
                "Images",
                "Date Extracted",
            ]
            rows = []

            for product in products:
                summary = format_product_summary(product)
                rows.append(
                    [
                        summary["id"],
                        summary["title"],
                        summary["price"],
                        summary["brand"],
                        summary["available"],
                        summary["images"],
                        summary["date_extracted"],
                    ]
                )

            print(tabulate(rows, headers=headers, tablefmt="grid"))
            print(f"\nTotal: {len(products)} product(s)")
        else:
            # Simplified list
            for i, product in enumerate(products):
                summary = format_product_summary(product)
                print(
                    f"{i+1}. [{summary['id']}] {summary['title']} - {summary['price']}"
                )
            print(f"\nTotal: {len(products)} product(s)")

    except Exception as e:
        print(f"Error searching products: {str(e)}")
        sys.exit(1)


def main():
    """Parse command line arguments and run the search."""
    parser = argparse.ArgumentParser(
        description="Search and display products from storage"
    )
    parser.add_argument(
        "--storage",
        default="./data",
        help="Path to storage directory (default: ./data)",
    )
    parser.add_argument("--query", help="Text query to filter products")
    parser.add_argument(
        "--sort",
        choices=["title", "price", "date_extracted", "brand"],
        help="Sort results by field",
    )
    parser.add_argument(
        "--available", action="store_true", help="Only show available products"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of products to display (default: 10)",
    )
    parser.add_argument(
        "--format",
        choices=["table", "json", "list", "detailed"],
        default="table",
        help="Output format (default: table)",
    )
    parser.add_argument("--id", help="Display details for a specific product ID")

    args = parser.parse_args()

    # Check if storage directory exists
    storage_path = Path(args.storage)
    if not storage_path.exists() or not storage_path.is_dir():
        print(f"Storage directory not found: {args.storage}")
        sys.exit(1)

    search_products(
        storage_path=args.storage,
        query=args.query,
        sort_by=args.sort,
        available_only=args.available,
        limit=args.limit,
        format_type=args.format,
        product_id=args.id,
    )


if __name__ == "__main__":
    main()
