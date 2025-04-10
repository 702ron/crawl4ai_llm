"""
Synchronous client implementation for the Crawl4AI SDK.

This module provides a synchronous wrapper around the asynchronous client
for users who prefer a traditional blocking API.
"""

import asyncio
from typing import Any, Dict, List, Optional, Union

from pydantic import HttpUrl

from .client import Crawl4AIClient
from .models import (
    BatchExtractionResult,
    ExportFormat,
    ExtractionRequest,
    ExtractionResult,
    ProductData,
    ProductFilter,
    SearchResult,
)


class SyncCrawl4AIClient:
    """
    Synchronous client for the Crawl4AI API.
    
    This class provides a synchronous interface to the Crawl4AI API by wrapping
    the asynchronous client. It's designed for users who prefer a traditional
    blocking API over asyncio.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8000",
        timeout: float = 60.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize the synchronous client.

        Args:
            api_key: API key for authentication
            base_url: Base URL for the API
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            retry_delay: Delay between retries in seconds
        """
        self._async_client = Crawl4AIClient(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        self._loop = None

    def _run_async(self, coro):
        """
        Run an asynchronous coroutine in a synchronous context.
        
        Args:
            coro: Coroutine to run
            
        Returns:
            Result of the coroutine
        """
        if self._loop is None:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        
        return self._loop.run_until_complete(coro)

    def close(self):
        """Close the client session."""
        if self._loop is not None:
            self._run_async(self._async_client.close())
            self._loop.close()
            self._loop = None

    def __enter__(self):
        """
        Enter context manager.
        
        Returns:
            The client instance
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit context manager and close the client."""
        self.close()

    def extract_product(self, request: ExtractionRequest) -> ExtractionResult:
        """
        Extract product data from a URL.

        Args:
            request: Extraction request parameters

        Returns:
            Extraction result with product data
        """
        return self._run_async(self._async_client.extract_product(request))

    def batch_extract_products(
        self,
        requests: List[ExtractionRequest],
        concurrency: int = 5,
        fail_fast: bool = False,
    ) -> BatchExtractionResult:
        """
        Extract multiple products in parallel.

        Args:
            requests: List of extraction requests
            concurrency: Maximum number of concurrent extractions
            fail_fast: Whether to stop on first failure

        Returns:
            Batch extraction result
        """
        return self._run_async(
            self._async_client.batch_extract_products(
                requests=requests,
                concurrency=concurrency,
                fail_fast=fail_fast,
            )
        )

    def get_product(self, product_id: str) -> Optional[ProductData]:
        """
        Get a product by ID.

        Args:
            product_id: ID of the product to retrieve

        Returns:
            Product data if found, None otherwise
        """
        return self._run_async(self._async_client.get_product(product_id))

    def update_product(self, product_id: str, product: ProductData) -> bool:
        """
        Update a product.

        Args:
            product_id: ID of the product to update
            product: Updated product data

        Returns:
            True if the update was successful, False otherwise
        """
        return self._run_async(self._async_client.update_product(product_id, product))

    def delete_product(self, product_id: str) -> bool:
        """
        Delete a product.

        Args:
            product_id: ID of the product to delete

        Returns:
            True if the deletion was successful, False otherwise
        """
        return self._run_async(self._async_client.delete_product(product_id))

    def search_products(
        self,
        filter: Optional[ProductFilter] = None,
        limit: int = 10,
        offset: int = 0,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> SearchResult:
        """
        Search for products based on filters.

        Args:
            filter: Filter for products
            limit: Maximum number of products to return
            offset: Offset for pagination
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            Search result with matching products
        """
        return self._run_async(
            self._async_client.search_products(
                filter=filter,
                limit=limit,
                offset=offset,
                sort_by=sort_by,
                sort_order=sort_order,
            )
        )

    def export_products(
        self,
        product_ids: Optional[List[str]] = None,
        filter: Optional[ProductFilter] = None,
        format: ExportFormat = ExportFormat.JSON,
        include_metadata: bool = False,
        flatten: bool = False,
    ) -> Union[List[Dict[str, Any]], str]:
        """
        Export products to JSON or CSV format.

        Args:
            product_ids: List of product IDs to export
            filter: Filter for selecting products to export
            format: Export format (JSON or CSV)
            include_metadata: Whether to include metadata in the export
            flatten: Whether to flatten nested structures (useful for CSV)

        Returns:
            Exported data as a list of dictionaries (JSON) or a string (CSV)
        """
        return self._run_async(
            self._async_client.export_products(
                product_ids=product_ids,
                filter=filter,
                format=format,
                include_metadata=include_metadata,
                flatten=flatten,
            )
        )

    def generate_schema(self, url: HttpUrl) -> Dict[str, Any]:
        """
        Generate an extraction schema for a URL.

        Args:
            url: URL to generate schema for

        Returns:
            Generated schema as a dictionary
        """
        return self._run_async(self._async_client.generate_schema(url)) 