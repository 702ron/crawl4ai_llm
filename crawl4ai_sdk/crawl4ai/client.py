"""
Client implementation for the Crawl4AI SDK.

This module provides a client for interacting with the Crawl4AI API to extract,
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

from .models import (
    APIError, 
    BatchExtractionResult, 
    ExportFormat,
    ExtractionMethod,
    ExtractionRequest, 
    ExtractionResult, 
    ProductData, 
    ProductFilter,
    SearchResult
)

logger = logging.getLogger(__name__)


class Crawl4AIClient:
    """Client for the Crawl4AI API."""

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
                response_text = await response.text()
                
                try:
                    response_data = json.loads(response_text)
                except json.JSONDecodeError:
                    response_data = {"detail": response_text}

                if response.status >= 400:
                    error_detail = response_data.get("detail", "Unknown error")
                    raise APIError(response.status, error_detail)

                return response_data

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if retry_count < self.max_retries:
                # Exponential backoff
                delay = self.retry_delay * (2 ** retry_count)
                logger.warning(
                    f"Request failed: {str(e)}. Retrying in {delay:.2f} seconds..."
                )
                await asyncio.sleep(delay)
                return await self._request(
                    method,
                    path,
                    params=params,
                    json_data=json_data,
                    retry_count=retry_count + 1,
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
                "store": request.store_result,
                "metadata": request.metadata
            }
            
            # Make API request
            response = await self._request("POST", "/extract", json_data=request_data)
            
            # Calculate extraction time
            extraction_time = time.time() - start_time
            
            # Process response
            success = response.get("success", False)
            error = response.get("error", None)
            product_id = response.get("product_id", None)
            messages = response.get("messages", [])
            
            # Create product data if available
            product_data = None
            if "data" in response and response["data"]:
                try:
                    product_data = ProductData.parse_obj(response["data"])
                except Exception as e:
                    logger.warning(f"Failed to parse product data: {str(e)}")
                    success = False
                    error = f"Failed to parse product data: {str(e)}"
            
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
            # Calculate extraction time even for failures
            extraction_time = time.time() - start_time
            
            logger.error(f"API error during extraction: {str(e)}")
            return ExtractionResult(
                success=False,
                product=None,
                messages=[],
                error=str(e),
                extraction_time=extraction_time,
            )

    async def batch_extract_products(
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
        start_time = time.time()
        
        # Create a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(concurrency)
        
        async def extract_with_semaphore(request: ExtractionRequest) -> ExtractionResult:
            async with semaphore:
                return await self.extract_product(request)
        
        # Process all requests
        tasks = []
        for request in requests:
            task = asyncio.create_task(extract_with_semaphore(request))
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = []
        for task in asyncio.as_completed(tasks):
            try:
                result = await task
                results.append(result)
                
                # If fail_fast is enabled and we have a failure, cancel remaining tasks
                if fail_fast and not result.success:
                    for remaining_task in tasks:
                        if not remaining_task.done():
                            remaining_task.cancel()
                    break
                
            except asyncio.CancelledError:
                # Task was cancelled due to fail_fast
                pass
            except Exception as e:
                logger.error(f"Error during batch extraction: {str(e)}")
                results.append(
                    ExtractionResult(
                        success=False,
                        product=None,
                        messages=[],
                        error=f"Unexpected error: {str(e)}",
                        extraction_time=0.0,
                    )
                )
        
        # Calculate statistics
        total_time = time.time() - start_time
        successful_count = sum(1 for r in results if r.success)
        failed_count = len(results) - successful_count
        
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
            product_id: ID of the product to retrieve

        Returns:
            Product data if found, None otherwise
        """
        try:
            response = await self._request("GET", f"/products/{product_id}")
            
            if "data" in response:
                return ProductData.parse_obj(response["data"])
            return None
            
        except APIError as e:
            if e.status_code == 404:
                logger.warning(f"Product {product_id} not found")
                return None
            raise

    async def update_product(self, product_id: str, product: ProductData) -> bool:
        """
        Update a product.

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
            
        except APIError as e:
            logger.error(f"Error updating product {product_id}: {str(e)}")
            return False

    async def delete_product(self, product_id: str) -> bool:
        """
        Delete a product.

        Args:
            product_id: ID of the product to delete

        Returns:
            True if the deletion was successful, False otherwise
        """
        try:
            response = await self._request("DELETE", f"/products/{product_id}")
            return response.get("success", False)
            
        except APIError as e:
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
        # Prepare query parameters
        params: Dict[str, Any] = {
            "limit": limit,
            "offset": offset,
        }
        
        if sort_by:
            params["sort_by"] = sort_by
            params["sort_order"] = sort_order
        
        # Add filter parameters if provided
        if filter:
            filter_dict = filter.dict(exclude_none=True)
            
            # Handle metadata filter specially
            if "metadata_filter" in filter_dict:
                metadata_filter = filter_dict.pop("metadata_filter")
                for key, value in metadata_filter.items():
                    params[f"metadata.{key}"] = value
            
            # Add remaining filter fields to params
            for key, value in filter_dict.items():
                if isinstance(value, datetime):
                    params[key] = value.isoformat()
                else:
                    params[key] = value
        
        try:
            # Make the API request
            response = await self._request("GET", "/products", params=params)
            
            # Parse products
            products = []
            for product_data in response.get("data", []):
                try:
                    product = ProductData.parse_obj(product_data)
                    products.append(product)
                except Exception as e:
                    logger.warning(f"Failed to parse product: {str(e)}")
            
            # Create search result
            result = SearchResult(
                products=products,
                total=response.get("total", len(products)),
                limit=limit,
                offset=offset,
            )
            
            return result
            
        except APIError as e:
            logger.error(f"Error searching products: {str(e)}")
            return SearchResult(
                products=[],
                total=0,
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
            product_ids: List of product IDs to export
            filter: Filter for selecting products to export
            format: Export format (JSON or CSV)
            include_metadata: Whether to include metadata in the export
            flatten: Whether to flatten nested structures (useful for CSV)

        Returns:
            Exported data as a list of dictionaries (JSON) or a string (CSV)
        """
        # Prepare request data
        request_data = {
            "format": format,
            "include_metadata": include_metadata,
            "flatten": flatten,
        }
        
        if product_ids:
            request_data["product_ids"] = product_ids
            
        if filter:
            request_data["filter"] = filter.dict(exclude_none=True)
        
        try:
            # Make the API request
            response = await self._request("POST", "/export", json_data=request_data)
            
            # Return the exported data
            if format == ExportFormat.JSON:
                return response.get("data", [])
            else:  # CSV
                return response.get("data", "")
            
        except APIError as e:
            logger.error(f"Error exporting products: {str(e)}")
            if format == ExportFormat.JSON:
                return []
            else:  # CSV
                return ""

    async def generate_schema(self, url: HttpUrl) -> Dict[str, Any]:
        """
        Generate an extraction schema for a URL.

        Args:
            url: URL to generate schema for

        Returns:
            Generated schema as a dictionary
        """
        try:
            response = await self._request(
                "POST", 
                "/generate-schema", 
                json_data={"url": str(url)}
            )
            
            return response.get("schema", {})
            
        except APIError as e:
            logger.error(f"Error generating schema: {str(e)}")
            return {} 