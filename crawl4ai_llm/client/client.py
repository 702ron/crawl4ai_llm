"""
Client implementation for the Crawl4AI LLM API.

This module provides a client for interacting with the Crawl4AI LLM API to extract,
search, and manage product data.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, cast

import aiohttp
from pydantic import HttpUrl, parse_obj_as

from ..models import ProductData
from .models import (APIError, BatchExtractionResult, ExportFormat,
                    ExtractionRequest, ExtractionResult, ProductFilter,
                    SearchResult)

logger = logging.getLogger(__name__)


class Crawl4AIClient:
    """Client for the Crawl4AI LLM API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8000",
        timeout: float = 60.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize the client.

        Args:
            api_key: API key for authentication
            base_url: Base URL for the API
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            retry_delay: Delay between retries in seconds
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure that an HTTP session exists and return it."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
        return self.session

    async def close(self) -> None:
        """Close the client session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the API.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path
            params: Query parameters
            json_data: JSON body data
            retry_count: Current retry count

        Returns:
            API response as a dictionary

        Raises:
            APIError: If the API returns an error
        """
        session = await self._ensure_session()
        url = f"{self.base_url}{path}"
        
        try:
            async with session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                timeout=self.timeout,
            ) as response:
                # Check if the response is successful
                if response.status >= 400:
                    response_text = await response.text()
                    try:
                        response_data = json.loads(response_text)
                        error_detail = response_data.get("detail", "Unknown error")
                    except json.JSONDecodeError:
                        error_detail = response_text
                    
                    raise APIError(response.status, error_detail)
                
                # Parse the response JSON
                try:
                    response_data = await response.json()
                    return response_data
                except json.JSONDecodeError:
                    response_text = await response.text()
                    raise APIError(
                        response.status, f"Failed to parse JSON response: {response_text}"
                    )
        
        except aiohttp.ClientError as e:
            # Handle network or client errors
            if retry_count < self.max_retries:
                retry_count += 1
                wait_time = self.retry_delay * (2 ** (retry_count - 1))  # Exponential backoff
                logger.warning(
                    f"Request failed: {str(e)}. Retrying in {wait_time:.2f} seconds "
                    f"(attempt {retry_count}/{self.max_retries})..."
                )
                await asyncio.sleep(wait_time)
                return await self._request(
                    method, path, params=params, json_data=json_data, retry_count=retry_count
                )
            else:
                logger.error(f"Request failed after {self.max_retries} retries: {str(e)}")
                raise APIError(500, f"Request failed: {str(e)}")

    async def extract_product(self, request: ExtractionRequest) -> ExtractionResult:
        """
        Extract product data from a URL.

        Args:
            request: Extraction request parameters

        Returns:
            Extraction result with product data
        """
        start_time = time.time()
        
        try:
            # Prepare request data
            request_data = {
                "url": str(request.url),
                "strategy": request.extraction_method,
                "fallback": request.use_fallback,
                "cache": True,  # Always use cache for performance
            }
            
            # Make API request
            response = await self._request("POST", "/extract", json_data=request_data)
            
            # Calculate extraction time
            extraction_time = time.time() - start_time
            
            # Process response
            success = True
            error = None
            product_id = response.get("metadata", {}).get("product_id")
            messages = []
            
            # Create product data if available
            product_data = None
            if "data" in response:
                try:
                    product_data = ProductData.parse_obj(response["data"])
                except Exception as e:
                    logger.warning(f"Failed to parse product data: {str(e)}")
                    success = False
                    error = f"Failed to parse product data: {str(e)}"
            
            # Add any messages from the response
            if "metadata" in response and "messages" in response["metadata"]:
                messages = response["metadata"]["messages"]
            
            # Prepare result
            result = ExtractionResult(
                success=success,
                product_id=product_id,
                product=product_data,
                messages=messages,
                error=error,
                extraction_time=extraction_time,
            )
            
            return result
        
        except APIError as e:
            # Handle API errors
            return ExtractionResult(
                success=False,
                product_id=None,
                product=None,
                messages=[],
                error=f"API error: {str(e)}",
                extraction_time=time.time() - start_time,
            )
        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Unexpected error during extraction: {str(e)}")
            return ExtractionResult(
                success=False,
                product_id=None,
                product=None,
                messages=[],
                error=f"Unexpected error: {str(e)}",
                extraction_time=time.time() - start_time,
            )

    async def batch_extract_products(
        self,
        requests: List[ExtractionRequest],
        concurrency: int = 5,
        fail_fast: bool = False,
    ) -> BatchExtractionResult:
        """
        Extract products from multiple URLs concurrently.

        Args:
            requests: List of extraction requests
            concurrency: Maximum number of concurrent extractions
            fail_fast: Whether to fail immediately on the first error

        Returns:
            Batch extraction result
        """
        start_time = time.time()
        
        # Create a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(concurrency)
        
        async def extract_with_semaphore(request: ExtractionRequest) -> ExtractionResult:
            """Extract a product with semaphore-based concurrency control."""
            async with semaphore:
                return await self.extract_product(request)
        
        # Extract products concurrently
        tasks = [extract_with_semaphore(request) for request in requests]
        
        try:
            # Wait for all tasks to complete
            if fail_fast:
                # In fail-fast mode, raise an exception on the first failure
                results = []
                for task in asyncio.as_completed(tasks):
                    result = await task
                    results.append(result)
                    if not result.success:
                        break
            else:
                # In normal mode, wait for all tasks to complete
                results = await asyncio.gather(*tasks)
        
        except asyncio.CancelledError:
            # Handle task cancellation
            for task in tasks:
                if not task.done():
                    task.cancel()
            raise
        
        # Calculate statistics
        successful_count = sum(1 for result in results if result.success)
        failed_count = len(results) - successful_count
        total_time = time.time() - start_time
        
        # Create batch extraction result
        return BatchExtractionResult(
            results=results,
            successful_count=successful_count,
            failed_count=failed_count,
            total_time=total_time,
        )

    async def get_product(self, product_id: str) -> Optional[ProductData]:
        """
        Get a product by ID.

        Args:
            product_id: ID of the product to get

        Returns:
            Product data if found, None otherwise
        """
        try:
            response = await self._request("GET", f"/products/{product_id}")
            return ProductData.parse_obj(response["data"])
        except APIError as e:
            if e.status_code == 404:
                logger.warning(f"Product {product_id} not found")
                return None
            raise
        except Exception as e:
            logger.error(f"Error fetching product {product_id}: {str(e)}")
            return None

    async def update_product(self, product_id: str, product: ProductData) -> bool:
        """
        Update a product by ID.

        Args:
            product_id: ID of the product to update
            product: Updated product data

        Returns:
            True if the update was successful, False otherwise
        """
        try:
            response = await self._request(
                "PUT", 
                f"/products/{product_id}", 
                json_data=product.dict(exclude_none=True)
            )
            return response.get("success", False)
        except Exception as e:
            logger.error(f"Error updating product {product_id}: {str(e)}")
            return False

    async def delete_product(self, product_id: str) -> bool:
        """
        Delete a product by ID.

        Args:
            product_id: ID of the product to delete

        Returns:
            True if the deletion was successful, False otherwise
        """
        try:
            response = await self._request("DELETE", f"/products/{product_id}")
            return response.get("success", False)
        except Exception as e:
            logger.error(f"Error deleting product {product_id}: {str(e)}")
            return False

    async def search_products(
        self,
        filter: Optional[ProductFilter] = None,
        limit: int = 10,
        offset: int = 0,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> SearchResult:
        """
        Search for products with filtering, pagination, and sorting.

        Args:
            filter: Filter criteria for products
            limit: Maximum number of products to return
            offset: Offset for pagination
            sort_by: Field to sort by
            sort_order: Sort order ('asc' or 'desc')

        Returns:
            Search result with matching products
        """
        # Build query parameters
        params: Dict[str, Any] = {
            "limit": limit,
            "offset": offset,
        }
        
        if sort_by:
            params["sort_by"] = sort_by
            params["sort_order"] = sort_order
        
        # Add filter criteria if available
        if filter:
            filter_dict = filter.dict(exclude_none=True)
            
            if "brand" in filter_dict:
                params["brand"] = filter_dict["brand"]
            
            if "title" in filter_dict:
                params["title"] = filter_dict["title"]
            
            if "price_min" in filter_dict:
                params["price_min"] = filter_dict["price_min"]
            
            if "price_max" in filter_dict:
                params["price_max"] = filter_dict["price_max"]
            
            if "created_after" in filter_dict:
                params["created_after"] = filter_dict["created_after"].isoformat()
            
            if "created_before" in filter_dict:
                params["created_before"] = filter_dict["created_before"].isoformat()
        
        # Make API request
        response = await self._request("GET", "/products", params=params)
        
        # Parse products
        products = [ProductData.parse_obj(item) for item in response]
        
        # Get total count (from the metadata of the first product or default to length)
        total = (
            response[0].get("metadata", {}).get("total_count", len(products))
            if response
            else 0
        )
        
        return SearchResult(
            products=products,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def export_products(
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
            product_ids: Specific product IDs to export, or None for filtering
            filter: Filter criteria if not exporting specific product IDs
            format: Export format (JSON or CSV)
            include_metadata: Whether to include metadata in the export
            flatten: Whether to flatten nested structures for CSV export

        Returns:
            JSON data as a list of dictionaries or CSV data as a string
        """
        # Build query parameters
        params: Dict[str, Any] = {}
        
        if product_ids:
            params["ids"] = ",".join(product_ids)
        
        # Add filter criteria if no specific product IDs
        if not product_ids and filter:
            filter_dict = filter.dict(exclude_none=True)
            
            if "brand" in filter_dict:
                params["brand"] = filter_dict["brand"]
            
            if "title" in filter_dict:
                params["title"] = filter_dict["title"]
            
            if "price_min" in filter_dict:
                params["price_min"] = filter_dict["price_min"]
            
            if "price_max" in filter_dict:
                params["price_max"] = filter_dict["price_max"]
            
            if "created_after" in filter_dict:
                params["created_after"] = filter_dict["created_after"].isoformat()
            
            if "created_before" in filter_dict:
                params["created_before"] = filter_dict["created_before"].isoformat()
        
        # Add export options
        params["include_metadata"] = "true" if include_metadata else "false"
        params["flatten"] = "true" if flatten else "false"
        
        # Choose export endpoint based on format
        if format == ExportFormat.JSON:
            response = await self._request("GET", "/export/json", params=params)
            return response.get("products", [])
        else:  # CSV
            session = await self._ensure_session()
            url = f"{self.base_url}/export/csv"
            
            async with session.get(url, params=params) as response:
                if response.status >= 400:
                    response_text = await response.text()
                    try:
                        response_data = json.loads(response_text)
                        error_detail = response_data.get("detail", "Unknown error")
                    except json.JSONDecodeError:
                        error_detail = response_text
                    
                    raise APIError(response.status, error_detail)
                
                return await response.text()

    async def generate_schema(self, url: HttpUrl) -> Dict[str, Any]:
        """
        Generate an extraction schema for a product page.

        Args:
            url: URL of the product page

        Returns:
            Generated schema
        """
        params = {"url": str(url)}
        response = await self._request("GET", "/schema", params=params)
        return response.get("schema", {})

    # Synchronous interface methods
    def extract_product_sync(self, request: ExtractionRequest) -> ExtractionResult:
        """
        Synchronous version of extract_product.

        Args:
            request: Extraction request parameters

        Returns:
            Extraction result with product data
        """
        return asyncio.run(self.extract_product(request))

    def batch_extract_products_sync(
        self,
        requests: List[ExtractionRequest],
        concurrency: int = 5,
        fail_fast: bool = False,
    ) -> BatchExtractionResult:
        """
        Synchronous version of batch_extract_products.

        Args:
            requests: List of extraction requests
            concurrency: Maximum number of concurrent extractions
            fail_fast: Whether to fail immediately on the first error

        Returns:
            Batch extraction result
        """
        return asyncio.run(self.batch_extract_products(requests, concurrency, fail_fast))

    def get_product_sync(self, product_id: str) -> Optional[ProductData]:
        """
        Synchronous version of get_product.

        Args:
            product_id: ID of the product to get

        Returns:
            Product data if found, None otherwise
        """
        return asyncio.run(self.get_product(product_id))

    def update_product_sync(self, product_id: str, product: ProductData) -> bool:
        """
        Synchronous version of update_product.

        Args:
            product_id: ID of the product to update
            product: Updated product data

        Returns:
            True if the update was successful, False otherwise
        """
        return asyncio.run(self.update_product(product_id, product))

    def delete_product_sync(self, product_id: str) -> bool:
        """
        Synchronous version of delete_product.

        Args:
            product_id: ID of the product to delete

        Returns:
            True if the deletion was successful, False otherwise
        """
        return asyncio.run(self.delete_product(product_id))

    def search_products_sync(
        self,
        filter: Optional[ProductFilter] = None,
        limit: int = 10,
        offset: int = 0,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> SearchResult:
        """
        Synchronous version of search_products.

        Args:
            filter: Filter criteria for products
            limit: Maximum number of products to return
            offset: Offset for pagination
            sort_by: Field to sort by
            sort_order: Sort order ('asc' or 'desc')

        Returns:
            Search result with matching products
        """
        return asyncio.run(
            self.search_products(filter, limit, offset, sort_by, sort_order)
        )

    def export_products_sync(
        self,
        product_ids: Optional[List[str]] = None,
        filter: Optional[ProductFilter] = None,
        format: ExportFormat = ExportFormat.JSON,
        include_metadata: bool = False,
        flatten: bool = False,
    ) -> Union[List[Dict[str, Any]], str]:
        """
        Synchronous version of export_products.

        Args:
            product_ids: Specific product IDs to export, or None for filtering
            filter: Filter criteria if not exporting specific product IDs
            format: Export format (JSON or CSV)
            include_metadata: Whether to include metadata in the export
            flatten: Whether to flatten nested structures for CSV export

        Returns:
            JSON data as a list of dictionaries or CSV data as a string
        """
        return asyncio.run(
            self.export_products(product_ids, filter, format, include_metadata, flatten)
        )

    def generate_schema_sync(self, url: HttpUrl) -> Dict[str, Any]:
        """
        Synchronous version of generate_schema.

        Args:
            url: URL of the product page

        Returns:
            Generated schema
        """
        return asyncio.run(self.generate_schema(url))

    def close_sync(self) -> None:
        """
        Synchronous version of close.
        """
        asyncio.run(self.close()) 