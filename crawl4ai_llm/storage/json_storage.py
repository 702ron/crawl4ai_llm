"""
JSON Storage Implementation.

This module implements file-based storage using JSON files.
"""

import json
import os
import hashlib
import aiofiles
import asyncio
import logging
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from datetime import datetime
import aiofiles.os as aio_os
from filelock import FileLock

from .base import (
    BaseStorage,
    StorageConnectionError,
    ProductNotFoundError,
    DuplicateProductError,
)

logger = logging.getLogger(__name__)


class JSONStorage(BaseStorage):
    """
    JSON file-based storage for product data.
    
    This storage implementation saves each product as a separate JSON file
    and maintains an index file for quick lookups and filtering.
    
    Attributes:
        directory: Directory path where product data is stored.
        index_file: Path to the index file.
        lock_timeout: Timeout in seconds for acquiring file locks.
        _index: In-memory cache of the product index.
        _locks: Dictionary of file locks for concurrent access.
    """
    
    def __init__(self, directory: str, lock_timeout: int = 30):
        """
        Initialize JSON storage.
        
        Args:
            directory: Directory path where product data is stored.
            lock_timeout: Timeout in seconds for acquiring file locks.
            
        Raises:
            StorageConnectionError: If the directory cannot be created or is not writable.
        """
        self.directory = os.path.abspath(directory)
        self.products_dir = os.path.join(self.directory, "products")
        self.index_file = os.path.join(self.directory, "product_index.json")
        self.index_lock_file = os.path.join(self.directory, "product_index.lock")
        self.lock_timeout = lock_timeout
        self._index: Dict[str, Dict[str, Any]] = {}
        self._locks: Dict[str, FileLock] = {}
        
        # Create directories if they don't exist
        try:
            os.makedirs(self.products_dir, exist_ok=True)
        except (OSError, PermissionError) as e:
            raise StorageConnectionError(f"Failed to create directories: {str(e)}")
        
        # Check if directories are writable
        if not os.access(self.products_dir, os.W_OK):
            raise StorageConnectionError(f"Directory is not writable: {self.products_dir}")
    
    def _get_product_id(self, product_data: Dict[str, Any]) -> str:
        """
        Generate a product ID based on product data.
        
        If product_data contains an 'id' field, it will be used.
        Otherwise, an ID will be generated based on:
        1. 'sku' + 'seller_id'
        2. 'mpn' + 'brand'
        3. 'gtin' or 'upc' or 'ean'
        4. 'url'
        5. Hash of the product name and other identifiers
        
        Args:
            product_data: Product data dictionary.
            
        Returns:
            str: Product ID.
        """
        # If product already has an ID, use it
        if "id" in product_data:
            return str(product_data["id"])
        
        # Generate ID based on common product identifiers
        identifiers = []
        
        # Option 1: SKU + Seller ID
        if "sku" in product_data and "seller_id" in product_data:
            return f"{product_data['seller_id']}_{product_data['sku']}"
        
        # Option 2: MPN + Brand
        if "mpn" in product_data and "brand" in product_data:
            return f"{product_data['brand']}_{product_data['mpn']}"
        
        # Option 3: GTIN, UPC, or EAN
        for id_type in ["gtin", "upc", "ean"]:
            if id_type in product_data and product_data[id_type]:
                return f"{id_type}_{product_data[id_type]}"
        
        # Option 4: URL
        if "url" in product_data and product_data["url"]:
            url_hash = hashlib.md5(product_data["url"].encode()).hexdigest()
            return f"url_{url_hash}"
        
        # Option 5: Product name and metadata hash
        hash_data = {"name": product_data.get("name", "")}
        
        for field in ["brand", "category", "model"]:
            if field in product_data:
                hash_data[field] = product_data[field]
        
        hash_str = json.dumps(hash_data, sort_keys=True)
        hash_digest = hashlib.md5(hash_str.encode()).hexdigest()
        
        return f"product_{hash_digest}"
    
    def _get_file_path(self, product_id: str) -> str:
        """
        Get the file path for a product.
        
        Args:
            product_id: Product ID.
            
        Returns:
            str: File path.
        """
        # Create a directory structure based on the first characters of the product ID
        # This helps to avoid having too many files in a single directory
        dir_prefix = product_id[:2]
        subdir = os.path.join(self.products_dir, dir_prefix)
        os.makedirs(subdir, exist_ok=True)
        
        return os.path.join(subdir, f"{product_id}.json")
    
    def _get_lock(self, file_path: str) -> FileLock:
        """
        Get a file lock for the given file path.
        
        Args:
            file_path: File path to lock.
            
        Returns:
            FileLock: The file lock.
        """
        if file_path not in self._locks:
            lock_file = f"{file_path}.lock"
            self._locks[file_path] = FileLock(lock_file, timeout=self.lock_timeout)
        
        return self._locks[file_path]
    
    async def _load_index(self) -> Dict[str, Dict[str, Any]]:
        """
        Load the product index from the index file.
        
        Returns:
            Dict[str, Dict[str, Any]]: Product index.
            
        Raises:
            StorageConnectionError: If the index file cannot be read.
        """
        index_lock = self._get_lock(self.index_file)
        
        try:
            with index_lock:
                if os.path.exists(self.index_file):
                    try:
                        async with aiofiles.open(self.index_file, "r") as f:
                            content = await f.read()
                            return json.loads(content) if content else {}
                    except (IOError, json.JSONDecodeError) as e:
                        logger.warning(f"Failed to read index file: {str(e)}")
                        return {}
                else:
                    return {}
        except TimeoutError:
            raise StorageConnectionError("Timeout acquiring index file lock")
    
    async def _save_index(self, index: Dict[str, Dict[str, Any]]) -> None:
        """
        Save the product index to the index file.
        
        Args:
            index: Product index.
            
        Raises:
            StorageConnectionError: If the index file cannot be written.
        """
        index_lock = self._get_lock(self.index_file)
        
        try:
            with index_lock:
                try:
                    async with aiofiles.open(self.index_file, "w") as f:
                        await f.write(json.dumps(index, indent=2))
                except IOError as e:
                    raise StorageConnectionError(f"Failed to write index file: {str(e)}")
        except TimeoutError:
            raise StorageConnectionError("Timeout acquiring index file lock")
    
    async def save_product(self, product_data: Dict[str, Any]) -> str:
        """
        Save a product to storage.
        
        Args:
            product_data: Product data dictionary.
            
        Returns:
            str: Product ID.
            
        Raises:
            DuplicateProductError: If a product with the same ID already exists.
            StorageConnectionError: If the product cannot be saved.
        """
        # Generate product ID
        product_id = self._get_product_id(product_data)
        
        # Check if product already exists
        index = await self._load_index()
        if product_id in index:
            raise DuplicateProductError(f"Product with ID {product_id} already exists")
        
        # Add product metadata to index
        metadata = {
            "id": product_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        
        # Add relevant fields to metadata for searching and filtering
        for field in ["name", "brand", "category", "price", "currency", "url", "sku", "seller_id"]:
            if field in product_data:
                metadata[field] = product_data[field]
        
        # Add product ID to the product data
        product_data["id"] = product_id
        
        # Save product data to file
        file_path = self._get_file_path(product_id)
        file_lock = self._get_lock(file_path)
        
        try:
            with file_lock:
                try:
                    async with aiofiles.open(file_path, "w") as f:
                        await f.write(json.dumps(product_data, indent=2))
                except IOError as e:
                    raise StorageConnectionError(f"Failed to write product file: {str(e)}")
        except TimeoutError:
            raise StorageConnectionError("Timeout acquiring product file lock")
        
        # Update index
        index[product_id] = metadata
        await self._save_index(index)
        
        return product_id
    
    async def save_products(self, products_data: List[Dict[str, Any]]) -> List[str]:
        """
        Save multiple products to the storage in a batch operation.
        
        Args:
            products_data: A list of dictionaries containing product data.
            
        Returns:
            List[str]: The IDs of the saved products.
            
        Raises:
            DuplicateProductError: If any product with the same ID already exists.
            StorageConnectionError: If a connection to the storage cannot be established.
        """
        if not products_data:
            return []
        
        # Load the current index
        index = await self._load_index()
        
        # Generate product IDs and check for duplicates
        products_with_ids = []
        product_ids = []
        new_index_entries = {}
        
        for product_data in products_data:
            product_id = self._get_product_id(product_data)
            
            if product_id in index:
                raise DuplicateProductError(f"Product with ID {product_id} already exists")
            
            # Add product ID to the product data
            product_data["id"] = product_id
            products_with_ids.append(product_data)
            product_ids.append(product_id)
            
            # Create metadata for index
            metadata = {
                "id": product_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            
            # Add relevant fields to metadata for searching and filtering
            for field in ["name", "brand", "category", "price", "currency", "url", "sku", "seller_id"]:
                if field in product_data:
                    metadata[field] = product_data[field]
            
            new_index_entries[product_id] = metadata
        
        # Save all products in parallel
        tasks = []
        for product_data in products_with_ids:
            tasks.append(self._save_product_file(product_data))
        
        await asyncio.gather(*tasks)
        
        # Update index with all new products
        index.update(new_index_entries)
        await self._save_index(index)
        
        return product_ids
    
    async def _save_product_file(self, product_data: Dict[str, Any]) -> None:
        """
        Save a product to a file without updating the index.
        
        Args:
            product_data: Product data dictionary.
            
        Raises:
            StorageConnectionError: If the product cannot be saved.
        """
        product_id = product_data["id"]
        file_path = self._get_file_path(product_id)
        file_lock = self._get_lock(file_path)
        
        try:
            with file_lock:
                try:
                    async with aiofiles.open(file_path, "w") as f:
                        await f.write(json.dumps(product_data, indent=2))
                except IOError as e:
                    raise StorageConnectionError(f"Failed to write product file: {str(e)}")
        except TimeoutError:
            raise StorageConnectionError("Timeout acquiring product file lock")
    
    async def get_product(self, product_id: str) -> Dict[str, Any]:
        """
        Get a product from storage.
        
        Args:
            product_id: Product ID.
            
        Returns:
            Dict[str, Any]: Product data.
            
        Raises:
            ProductNotFoundError: If the product is not found.
            StorageConnectionError: If the product cannot be retrieved.
        """
        # Check if product exists in index
        index = await self._load_index()
        if product_id not in index:
            # Try to load the product directly from file as a fallback
            file_path = self._get_file_path(product_id)
            if not await aio_os.path.exists(file_path):
                raise ProductNotFoundError(f"Product with ID {product_id} not found")
        
        # Get product data from file
        file_path = self._get_file_path(product_id)
        file_lock = self._get_lock(file_path)
        
        try:
            with file_lock:
                try:
                    if not await aio_os.path.exists(file_path):
                        raise ProductNotFoundError(f"Product with ID {product_id} not found")
                    
                    async with aiofiles.open(file_path, "r") as f:
                        content = await f.read()
                        return json.loads(content)
                except (IOError, json.JSONDecodeError) as e:
                    raise StorageConnectionError(f"Failed to read product file: {str(e)}")
        except TimeoutError:
            raise StorageConnectionError("Timeout acquiring product file lock")
    
    async def get_products(self, product_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get multiple products from the storage by their IDs in a batch operation.
        
        Args:
            product_ids: A list of product IDs to retrieve.
            
        Returns:
            List[Dict[str, Any]]: The product data for each found product.
            
        Raises:
            ProductNotFoundError: If any of the products are not found.
            StorageConnectionError: If a connection to the storage cannot be established.
        """
        if not product_ids:
            return []
        
        # Load products in parallel
        tasks = []
        for product_id in product_ids:
            tasks.append(self.get_product(product_id))
        
        return await asyncio.gather(*tasks)
    
    async def update_product(self, product_id: str, product_data: Dict[str, Any]) -> str:
        """
        Update a product in storage.
        
        Args:
            product_id: Product ID.
            product_data: Updated product data.
            
        Returns:
            str: Product ID.
            
        Raises:
            ProductNotFoundError: If the product is not found.
            StorageConnectionError: If the product cannot be updated.
        """
        # Check if product exists
        index = await self._load_index()
        if product_id not in index:
            # Try to load the product directly from file as a fallback
            file_path = self._get_file_path(product_id)
            if not await aio_os.path.exists(file_path):
                raise ProductNotFoundError(f"Product with ID {product_id} not found")
        
        # Ensure the product ID is not changed
        product_data["id"] = product_id
        
        # Update product metadata in index
        metadata = index.get(product_id, {})
        metadata["updated_at"] = datetime.now().isoformat()
        
        # Update relevant fields in metadata for searching and filtering
        for field in ["name", "brand", "category", "price", "currency", "url", "sku", "seller_id"]:
            if field in product_data:
                metadata[field] = product_data[field]
        
        # Save updated product data to file
        file_path = self._get_file_path(product_id)
        file_lock = self._get_lock(file_path)
        
        try:
            with file_lock:
                try:
                    async with aiofiles.open(file_path, "w") as f:
                        await f.write(json.dumps(product_data, indent=2))
                except IOError as e:
                    raise StorageConnectionError(f"Failed to write product file: {str(e)}")
        except TimeoutError:
            raise StorageConnectionError("Timeout acquiring product file lock")
        
        # Update index
        index[product_id] = metadata
        await self._save_index(index)
        
        return product_id
    
    async def update_products(self, products: List[Dict[str, Any]]) -> List[str]:
        """
        Update multiple products in the storage in a batch operation.
        
        Args:
            products: A list of dictionaries containing updated product data with their IDs.
                     Each dictionary should include a product_id key.
            
        Returns:
            List[str]: The IDs of the updated products.
            
        Raises:
            ProductNotFoundError: If any of the products are not found.
            StorageConnectionError: If a connection to the storage cannot be established.
        """
        if not products:
            return []
        
        # Load the current index
        index = await self._load_index()
        
        # Verify all products exist and prepare updates
        products_to_update = []
        product_ids = []
        index_updates = {}
        
        for product_data in products:
            if "id" not in product_data:
                raise ValueError("Each product must include an 'id' field")
            
            product_id = product_data["id"]
            product_ids.append(product_id)
            
            # Check if product exists in index or file
            if product_id not in index:
                file_path = self._get_file_path(product_id)
                if not await aio_os.path.exists(file_path):
                    raise ProductNotFoundError(f"Product with ID {product_id} not found")
            
            # Ensure the product ID is not changed
            product_data["id"] = product_id
            products_to_update.append(product_data)
            
            # Update metadata in index
            metadata = index.get(product_id, {})
            metadata["updated_at"] = datetime.now().isoformat()
            
            # Update relevant fields in metadata for searching and filtering
            for field in ["name", "brand", "category", "price", "currency", "url", "sku", "seller_id"]:
                if field in product_data:
                    metadata[field] = product_data[field]
            
            index_updates[product_id] = metadata
        
        # Save all products in parallel
        tasks = []
        for product_data in products_to_update:
            tasks.append(self._save_product_file(product_data))
        
        await asyncio.gather(*tasks)
        
        # Update index with all updated products
        index.update(index_updates)
        await self._save_index(index)
        
        return product_ids
    
    async def delete_product(self, product_id: str) -> bool:
        """
        Delete a product from storage.
        
        Args:
            product_id: Product ID.
            
        Returns:
            bool: True if the product was deleted, False otherwise.
            
        Raises:
            ProductNotFoundError: If the product is not found.
            StorageConnectionError: If the product cannot be deleted.
        """
        # Check if product exists
        index = await self._load_index()
        file_path = self._get_file_path(product_id)
        
        if product_id not in index and not await aio_os.path.exists(file_path):
            raise ProductNotFoundError(f"Product with ID {product_id} not found")
        
        # Delete product file
        file_lock = self._get_lock(file_path)
        
        try:
            with file_lock:
                try:
                    if await aio_os.path.exists(file_path):
                        await aio_os.unlink(file_path)
                except IOError as e:
                    raise StorageConnectionError(f"Failed to delete product file: {str(e)}")
        except TimeoutError:
            raise StorageConnectionError("Timeout acquiring product file lock")
        
        # Remove product from index
        if product_id in index:
            del index[product_id]
            await self._save_index(index)
        
        return True
    
    async def delete_products(self, product_ids: List[str]) -> int:
        """
        Delete multiple products from the storage in a batch operation.
        
        Args:
            product_ids: A list of product IDs to delete.
            
        Returns:
            int: The number of products deleted.
            
        Raises:
            ProductNotFoundError: If any of the products are not found.
            StorageConnectionError: If a connection to the storage cannot be established.
        """
        if not product_ids:
            return 0
        
        # Load the current index
        index = await self._load_index()
        
        # Verify all products exist
        missing_products = []
        for product_id in product_ids:
            file_path = self._get_file_path(product_id)
            if product_id not in index and not await aio_os.path.exists(file_path):
                missing_products.append(product_id)
        
        if missing_products:
            raise ProductNotFoundError(f"Products not found: {', '.join(missing_products)}")
        
        # Delete all product files in parallel
        tasks = []
        for product_id in product_ids:
            tasks.append(self._delete_product_file(product_id))
        
        await asyncio.gather(*tasks)
        
        # Remove products from index
        updated = False
        for product_id in product_ids:
            if product_id in index:
                del index[product_id]
                updated = True
        
        if updated:
            await self._save_index(index)
        
        return len(product_ids)
    
    async def _delete_product_file(self, product_id: str) -> None:
        """
        Delete a product file without updating the index.
        
        Args:
            product_id: Product ID.
            
        Raises:
            StorageConnectionError: If the product cannot be deleted.
        """
        file_path = self._get_file_path(product_id)
        file_lock = self._get_lock(file_path)
        
        try:
            with file_lock:
                try:
                    if await aio_os.path.exists(file_path):
                        await aio_os.unlink(file_path)
                except IOError as e:
                    raise StorageConnectionError(f"Failed to delete product file: {str(e)}")
        except TimeoutError:
            raise StorageConnectionError("Timeout acquiring product file lock")
    
    async def list_products(
        self,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 50,
        sort_by: Optional[str] = None,
        sort_order: str = "asc"
    ) -> Dict[str, Any]:
        """
        List products with optional filtering, pagination and sorting.
        
        Args:
            filters: Optional dictionary of field:value to filter products.
            page: Page number (1-indexed).
            page_size: Number of items per page.
            sort_by: Field to sort by.
            sort_order: Sort order, either "asc" or "desc".
            
        Returns:
            Dict[str, Any]: Dictionary containing:
                - items: List of products
                - total: Total number of products matching the filters
                - page: Current page number
                - page_size: Number of items per page
                - total_pages: Total number of pages
            
        Raises:
            StorageConnectionError: If the products cannot be listed.
        """
        # Load index
        index = await self._load_index()
        
        # Apply filters
        filtered_products = []
        for product_id, metadata in index.items():
            if filters and not self._matches_filters(metadata, filters):
                continue
            
            filtered_products.append(metadata)
        
        # Apply sorting
        if sort_by:
            reverse = sort_order.lower() == "desc"
            filtered_products.sort(
                key=lambda p: p.get(sort_by, ""),
                reverse=reverse
            )
        
        # Apply pagination
        total = len(filtered_products)
        total_pages = (total + page_size - 1) // page_size
        
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total)
        
        page_products = filtered_products[start_idx:end_idx]
        
        # Load full product data for the page
        product_ids = [p["id"] for p in page_products]
        
        product_tasks = []
        for product_id in product_ids:
            product_tasks.append(self.get_product(product_id))
        
        try:
            items = await asyncio.gather(*product_tasks)
        except ProductNotFoundError:
            # Handle case where a product was deleted after loading the index
            # Refresh the index and try again
            new_index = await self._load_index()
            # Only keep products that still exist
            product_ids = [pid for pid in product_ids if pid in new_index]
            
            product_tasks = []
            for product_id in product_ids:
                product_tasks.append(self.get_product(product_id))
            
            items = await asyncio.gather(*product_tasks)
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }
    
    def _matches_filters(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """
        Check if a product's metadata matches the given filters.
        
        Args:
            metadata: Product metadata.
            filters: Filters to apply.
            
        Returns:
            bool: True if the product matches all filters, False otherwise.
        """
        for field, value in filters.items():
            # Handle special filter operations
            if isinstance(value, dict):
                for op, op_value in value.items():
                    if op == "eq" and metadata.get(field) != op_value:
                        return False
                    elif op == "neq" and metadata.get(field) == op_value:
                        return False
                    elif op == "gt" and (field not in metadata or metadata[field] <= op_value):
                        return False
                    elif op == "gte" and (field not in metadata or metadata[field] < op_value):
                        return False
                    elif op == "lt" and (field not in metadata or metadata[field] >= op_value):
                        return False
                    elif op == "lte" and (field not in metadata or metadata[field] > op_value):
                        return False
                    elif op == "in" and (field not in metadata or metadata[field] not in op_value):
                        return False
                    elif op == "nin" and (field in metadata and metadata[field] in op_value):
                        return False
                    elif op == "contains" and (field not in metadata or op_value not in str(metadata[field])):
                        return False
            else:
                # Simple equality check
                if field not in metadata or metadata[field] != value:
                    return False
        
        return True