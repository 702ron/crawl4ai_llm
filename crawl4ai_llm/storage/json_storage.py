"""
JSON file-based storage implementation for product data.

This module provides a simple file-based storage option using JSON files.
Each product is stored in a separate JSON file.
"""

import os
import json
import uuid
import asyncio
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
import aiofiles
import glob
from pathlib import Path
import filelock
import threading

from ..models import ProductData
from .base import (
    BaseStorage, 
    StorageError, 
    ProductNotFoundError, 
    DuplicateProductError, 
    StorageConnectionError
)

logger = logging.getLogger(__name__)


class JSONStorage(BaseStorage):
    """
    File-based storage implementation using JSON files.
    
    This implementation stores each product in a separate JSON file
    in the specified directory.
    """
    
    def __init__(self, 
                 storage_dir: str, 
                 create_if_missing: bool = True,
                 use_uuid: bool = True):
        """
        Initialize the JSON storage.
        
        Args:
            storage_dir: Directory to store JSON files
            create_if_missing: Create the directory if it doesn't exist
            use_uuid: Use UUIDs as filenames (if False, uses product SKU or URL hash)
        """
        self.storage_dir = Path(storage_dir)
        self.use_uuid = use_uuid
        self._locks = {}
        self._locks_lock = threading.Lock()
        
        if not self.storage_dir.exists():
            if create_if_missing:
                try:
                    self.storage_dir.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    raise StorageConnectionError(f"Failed to create storage directory: {e}")
            else:
                raise StorageConnectionError(f"Storage directory does not exist: {self.storage_dir}")
                
        # Create an index file if it doesn't exist
        self.index_path = self.storage_dir / "index.json"
        self.index_lock_path = self.storage_dir / "index.lock"
        
        if not self.index_path.exists():
            try:
                with open(self.index_path, "w") as f:
                    json.dump({}, f)
            except OSError as e:
                raise StorageConnectionError(f"Failed to create index file: {e}")
                
        logger.info(f"Initialized JSON storage at {self.storage_dir}")
    
    def _get_lock(self, file_path: Path) -> filelock.FileLock:
        """
        Get a lock for a file.
        
        Args:
            file_path: Path to get a lock for
            
        Returns:
            filelock.FileLock: Lock for the file
        """
        lock_path = Path(f"{file_path}.lock")
        
        with self._locks_lock:
            if str(lock_path) not in self._locks:
                self._locks[str(lock_path)] = filelock.FileLock(lock_path)
                
            return self._locks[str(lock_path)]
    
    def _get_product_id(self, product: ProductData) -> str:
        """
        Generate a product ID based on configuration.
        
        Args:
            product: The product data
            
        Returns:
            str: A unique ID for the product
        """
        if self.use_uuid:
            return str(uuid.uuid4())
            
        # Try to use SKU or other identifier
        if product.identifiers and product.identifiers.get("sku"):
            return f"sku_{product.identifiers['sku']}"
        elif product.identifiers and product.identifiers.get("upc"):
            return f"upc_{product.identifiers['upc']}"
        elif product.identifiers and product.identifiers.get("ean"):
            return f"ean_{product.identifiers['ean']}"
            
        # Fall back to title + brand hash
        import hashlib
        hash_input = f"{product.title}_{product.brand}_{product.url}"
        return f"hash_{hashlib.md5(hash_input.encode()).hexdigest()}"
    
    def _get_file_path(self, product_id: str) -> Path:
        """
        Get the file path for a product ID.
        
        Args:
            product_id: The product ID
            
        Returns:
            Path: The file path
        """
        # Ensure product_id is safe for file system use
        safe_id = product_id.replace('/', '_').replace('\\', '_')
        return self.storage_dir / f"{safe_id}.json"
    
    async def _load_index(self) -> Dict[str, Any]:
        """
        Load the index file.
        
        Returns:
            Dict[str, Any]: The index data
        """
        lock = self._get_lock(self.index_path)
        
        try:
            with lock.acquire(timeout=10):  # 10 second timeout
                with open(self.index_path, "r") as f:
                    content = f.read()
                    return json.loads(content) if content else {}
        except filelock.Timeout:
            logger.error("Timeout waiting for index lock")
            # Return empty dict as fallback
            return {}
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load index: {e}")
            return {}
    
    async def _save_index(self, index_data: Dict[str, Any]) -> None:
        """
        Save the index file.
        
        Args:
            index_data: The index data to save
        """
        lock = self._get_lock(self.index_path)
        
        try:
            with lock.acquire(timeout=10):  # 10 second timeout
                with open(self.index_path, "w") as f:
                    json.dump(index_data, f, indent=2)
        except filelock.Timeout:
            logger.error("Timeout waiting for index lock")
            raise StorageError("Timeout waiting for index lock")
        except OSError as e:
            logger.error(f"Failed to save index: {e}")
            raise StorageError(f"Failed to save index: {e}")
    
    async def save_product(self, product: ProductData) -> str:
        """
        Save a product to a JSON file.
        
        Args:
            product: The product data to save
            
        Returns:
            str: The product ID
            
        Raises:
            DuplicateProductError: If the product already exists
            StorageError: If there's an error saving the product
        """
        # Generate ID and file path
        product_id = self._get_product_id(product)
        file_path = self._get_file_path(product_id)
        
        # Check if the product already exists
        if file_path.exists() and not self.use_uuid:
            raise DuplicateProductError(f"Product with ID {product_id} already exists")
            
        # Add metadata
        product_dict = product.dict()
        product_dict["metadata"] = product_dict.get("metadata", {})
        product_dict["metadata"]["saved_at"] = datetime.utcnow().isoformat()
        product_dict["metadata"]["product_id"] = product_id
        
        # Get lock for the file
        lock = self._get_lock(file_path)
        
        try:
            # Save the product
            with lock.acquire(timeout=10):  # 10 second timeout
                with open(file_path, "w") as f:
                    json.dump(product_dict, f, indent=2, default=str)
                
            # Update the index
            index = await self._load_index()
            index[product_id] = {
                "title": product.title,
                "url": product.url,
                "brand": product.brand,
                "saved_at": product_dict["metadata"]["saved_at"],
                "file_path": file_path.name
            }
            await self._save_index(index)
            
            logger.info(f"Saved product {product_id} to {file_path}")
            return product_id
        except filelock.Timeout:
            logger.error(f"Timeout waiting for file lock: {file_path}")
            raise StorageError(f"Timeout waiting for file lock: {file_path}")    
        except OSError as e:
            logger.error(f"Failed to save product: {e}")
            raise StorageError(f"Failed to save product: {e}")
    
    async def save_products(self, products: List[ProductData]) -> List[str]:
        """
        Save multiple products in a batch operation.
        
        Args:
            products: List of product data objects to save
            
        Returns:
            List[str]: List of product IDs that were successfully saved
            
        Raises:
            StorageError: If there's an error saving any product
        """
        if not products:
            return []
            
        # Generate IDs for all products
        product_ids = []
        products_with_ids = []
        
        # First pass - generate IDs and check for duplicates
        for product in products:
            product_id = self._get_product_id(product)
            file_path = self._get_file_path(product_id)
            
            # Check if the product already exists (non-UUID mode only)
            if file_path.exists() and not self.use_uuid:
                logger.warning(f"Skipping duplicate product with ID {product_id}")
                continue
                
            product_ids.append(product_id)
            
            # Add metadata
            product_dict = product.dict()
            product_dict["metadata"] = product_dict.get("metadata", {})
            product_dict["metadata"]["saved_at"] = datetime.utcnow().isoformat()
            product_dict["metadata"]["product_id"] = product_id
            
            products_with_ids.append((product, product_id, product_dict, file_path))
            
        # No valid products to save
        if not products_with_ids:
            return []
            
        # Second pass - save all files
        index = await self._load_index()
        
        async def save_one_product(product_tuple):
            product, product_id, product_dict, file_path = product_tuple
            
            # Get lock for the file
            lock = self._get_lock(file_path)
            
            try:
                # Save the product
                with lock.acquire(timeout=10):  # 10 second timeout
                    with open(file_path, "w") as f:
                        json.dump(product_dict, f, indent=2, default=str)
                
                # Update the index (in memory)
                index[product_id] = {
                    "title": product.title,
                    "url": product.url,
                    "brand": product.brand,
                    "saved_at": product_dict["metadata"]["saved_at"],
                    "file_path": file_path.name
                }
                
                return True
            except (filelock.Timeout, OSError) as e:
                logger.error(f"Failed to save product {product_id}: {e}")
                return False
                
        # Save all products concurrently
        save_tasks = [save_one_product(product_tuple) for product_tuple in products_with_ids]
        results = await asyncio.gather(*save_tasks)
        
        # Only keep IDs that were successfully saved
        successful_ids = [product_ids[i] for i, success in enumerate(results) if success]
        
        # Save the updated index
        try:
            await self._save_index(index)
        except StorageError as e:
            logger.error(f"Failed to save index after batch operation: {e}")
            
        logger.info(f"Saved {len(successful_ids)} products out of {len(products)} in batch")
        return successful_ids
    
    async def get_product(self, product_id: str) -> Optional[ProductData]:
        """
        Retrieve a product from storage by ID.
        
        Args:
            product_id: The ID of the product to retrieve
            
        Returns:
            Optional[ProductData]: The product if found, None otherwise
            
        Raises:
            ProductNotFoundError: If the product is not found
            StorageError: If there's an error retrieving the product
        """
        file_path = self._get_file_path(product_id)
        
        if not file_path.exists():
            raise ProductNotFoundError(f"Product with ID {product_id} not found")
        
        # Get lock for the file
        lock = self._get_lock(file_path)
            
        try:
            with lock.acquire(timeout=10, poll_intervall=0.1):  # 10 second timeout, check every 100ms
                with open(file_path, "r") as f:
                    content = f.read()
                    product_dict = json.loads(content)
                    return ProductData(**product_dict)
        except filelock.Timeout:
            logger.error(f"Timeout waiting for file lock: {file_path}")
            raise StorageError(f"Timeout waiting for file lock: {file_path}")
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Failed to read product {product_id}: {e}")
            raise StorageError(f"Failed to read product {product_id}: {e}")
    
    async def get_products(self, product_ids: List[str]) -> Dict[str, ProductData]:
        """
        Retrieve multiple products by their IDs in a batch operation.
        
        Args:
            product_ids: List of product IDs to retrieve
            
        Returns:
            Dict[str, ProductData]: Dictionary mapping product IDs to their data
            
        Raises:
            StorageError: If there's an error retrieving any product
        """
        if not product_ids:
            return {}
            
        result = {}
        
        async def get_one_product(product_id):
            try:
                product = await self.get_product(product_id)
                return product_id, product
            except ProductNotFoundError:
                logger.warning(f"Product with ID {product_id} not found during batch retrieval")
                return product_id, None
            except StorageError as e:
                logger.error(f"Error retrieving product {product_id}: {e}")
                return product_id, None
                
        # Retrieve all products concurrently
        tasks = [get_one_product(product_id) for product_id in product_ids]
        product_results = await asyncio.gather(*tasks)
        
        # Filter out unsuccessful retrievals
        for product_id, product in product_results:
            if product is not None:
                result[product_id] = product
                
        logger.info(f"Retrieved {len(result)} products out of {len(product_ids)} in batch")
        return result
    
    async def update_product(self, product_id: str, product: ProductData) -> bool:
        """
        Update an existing product in storage.
        
        Args:
            product_id: The ID of the product to update
            product: The updated product data
            
        Returns:
            bool: True if the update was successful, False otherwise
            
        Raises:
            ProductNotFoundError: If the product is not found
            StorageError: If there's an error updating the product
        """
        file_path = self._get_file_path(product_id)
        
        if not file_path.exists():
            raise ProductNotFoundError(f"Product with ID {product_id} not found")
            
        # Get lock for the file
        lock = self._get_lock(file_path)
            
        try:
            # Get existing product to preserve metadata
            existing_product = await self.get_product(product_id)
            existing_dict = existing_product.dict()
            
            # Update with new data
            product_dict = product.dict()
            product_dict["metadata"] = existing_dict.get("metadata", {})
            product_dict["metadata"].update(product_dict.get("metadata", {}))
            product_dict["metadata"]["updated_at"] = datetime.utcnow().isoformat()
            product_dict["metadata"]["product_id"] = product_id
            
            # Save the updated product
            with lock.acquire(timeout=10):  # 10 second timeout
                with open(file_path, "w") as f:
                    json.dump(product_dict, f, indent=2, default=str)
                
            # Update the index
            index = await self._load_index()
            if product_id in index:
                index[product_id].update({
                    "title": product.title,
                    "url": product.url,
                    "brand": product.brand,
                    "updated_at": product_dict["metadata"]["updated_at"]
                })
                await self._save_index(index)
                
            logger.info(f"Updated product {product_id}")
            return True
        except filelock.Timeout:
            logger.error(f"Timeout waiting for file lock: {file_path}")
            raise StorageError(f"Timeout waiting for file lock: {file_path}")    
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Failed to update product {product_id}: {e}")
            raise StorageError(f"Failed to update product {product_id}: {e}")
    
    async def update_products(self, updates: Dict[str, ProductData]) -> Dict[str, bool]:
        """
        Update multiple products in a batch operation.
        
        Args:
            updates: Dictionary mapping product IDs to updated product data
            
        Returns:
            Dict[str, bool]: Dictionary mapping product IDs to update success status
            
        Raises:
            StorageError: If there's an error with the batch operation
        """
        if not updates:
            return {}
            
        # Load the index once for all updates
        index = await self._load_index()
        results = {}
        
        async def update_one_product(product_id, product):
            try:
                file_path = self._get_file_path(product_id)
                
                if not file_path.exists():
                    logger.warning(f"Product with ID {product_id} not found during batch update")
                    return product_id, False
                    
                # Get lock for the file
                lock = self._get_lock(file_path)
                
                try:
                    # Get existing product to preserve metadata
                    existing_product = await self.get_product(product_id)
                    existing_dict = existing_product.dict()
                    
                    # Update with new data
                    product_dict = product.dict()
                    product_dict["metadata"] = existing_dict.get("metadata", {})
                    product_dict["metadata"].update(product_dict.get("metadata", {}))
                    product_dict["metadata"]["updated_at"] = datetime.utcnow().isoformat()
                    product_dict["metadata"]["product_id"] = product_id
                    
                    # Save the updated product
                    with lock.acquire(timeout=10):  # 10 second timeout
                        with open(file_path, "w") as f:
                            json.dump(product_dict, f, indent=2, default=str)
                    
                    # Update the index (in memory)
                    if product_id in index:
                        index[product_id].update({
                            "title": product.title,
                            "url": product.url,
                            "brand": product.brand,
                            "updated_at": product_dict["metadata"]["updated_at"]
                        })
                    
                    return product_id, True
                except (filelock.Timeout, OSError, json.JSONDecodeError, ProductNotFoundError) as e:
                    logger.error(f"Failed to update product {product_id}: {e}")
                    return product_id, False
            except Exception as e:
                logger.error(f"Unexpected error updating product {product_id}: {e}")
                return product_id, False
                
        # Update all products concurrently
        update_tasks = [update_one_product(product_id, product) for product_id, product in updates.items()]
        update_results = await asyncio.gather(*update_tasks)
        
        # Process results
        for product_id, success in update_results:
            results[product_id] = success
            
        # Save the updated index
        try:
            await self._save_index(index)
        except StorageError as e:
            logger.error(f"Failed to save index after batch update: {e}")
            
        logger.info(f"Updated {sum(results.values())} products out of {len(updates)} in batch")
        return results
    
    async def delete_product(self, product_id: str) -> bool:
        """
        Delete a product from storage.
        
        Args:
            product_id: The ID of the product to delete
            
        Returns:
            bool: True if the deletion was successful, False otherwise
            
        Raises:
            ProductNotFoundError: If the product is not found
            StorageError: If there's an error deleting the product
        """
        file_path = self._get_file_path(product_id)
        
        if not file_path.exists():
            raise ProductNotFoundError(f"Product with ID {product_id} not found")
        
        # Get lock for the file
        lock = self._get_lock(file_path)
            
        try:
            # Delete the file
            with lock.acquire(timeout=10):  # 10 second timeout
                file_path.unlink()
            
            # Release the lock and remove the lock file if it exists
            lock_path = Path(f"{file_path}.lock")
            with self._locks_lock:
                if str(lock_path) in self._locks:
                    del self._locks[str(lock_path)]
            if lock_path.exists():
                try:
                    lock_path.unlink()
                except OSError:
                    # It's okay if we can't delete the lock file
                    pass
            
            # Update the index
            index = await self._load_index()
            if product_id in index:
                del index[product_id]
                await self._save_index(index)
                
            logger.info(f"Deleted product {product_id}")
            return True
        except filelock.Timeout:
            logger.error(f"Timeout waiting for file lock: {file_path}")
            raise StorageError(f"Timeout waiting for file lock: {file_path}")    
        except OSError as e:
            logger.error(f"Failed to delete product {product_id}: {e}")
            raise StorageError(f"Failed to delete product {product_id}: {e}")
    
    async def delete_products(self, product_ids: List[str]) -> Dict[str, bool]:
        """
        Delete multiple products in a batch operation.
        
        Args:
            product_ids: List of product IDs to delete
            
        Returns:
            Dict[str, bool]: Dictionary mapping product IDs to deletion success status
            
        Raises:
            StorageError: If there's an error with the batch operation
        """
        if not product_ids:
            return {}
            
        # Load the index once for all deletions
        index = await self._load_index()
        results = {}
        
        async def delete_one_product(product_id):
            try:
                file_path = self._get_file_path(product_id)
                
                if not file_path.exists():
                    logger.warning(f"Product with ID {product_id} not found during batch deletion")
                    return product_id, False
                    
                # Get lock for the file
                lock = self._get_lock(file_path)
                
                try:
                    # Delete the file
                    with lock.acquire(timeout=10):  # 10 second timeout
                        file_path.unlink()
                    
                    # Release the lock and remove the lock file if it exists
                    lock_path = Path(f"{file_path}.lock")
                    with self._locks_lock:
                        if str(lock_path) in self._locks:
                            del self._locks[str(lock_path)]
                    if lock_path.exists():
                        try:
                            lock_path.unlink()
                        except OSError:
                            # It's okay if we can't delete the lock file
                            pass
                    
                    # Update the index in memory
                    if product_id in index:
                        del index[product_id]
                    
                    return product_id, True
                except (filelock.Timeout, OSError) as e:
                    logger.error(f"Failed to delete product {product_id}: {e}")
                    return product_id, False
            except Exception as e:
                logger.error(f"Unexpected error deleting product {product_id}: {e}")
                return product_id, False
                
        # Delete all products concurrently
        delete_tasks = [delete_one_product(product_id) for product_id in product_ids]
        delete_results = await asyncio.gather(*delete_tasks)
        
        # Process results
        for product_id, success in delete_results:
            results[product_id] = success
            
        # Save the updated index
        try:
            await self._save_index(index)
        except StorageError as e:
            logger.error(f"Failed to save index after batch deletion: {e}")
            
        logger.info(f"Deleted {sum(results.values())} products out of {len(product_ids)} in batch")
        return results
    
    async def list_products(self, 
                    filters: Optional[Dict[str, Any]] = None, 
                    limit: int = 100, 
                    offset: int = 0,
                    sort_by: Optional[str] = None,
                    sort_order: str = "asc") -> Tuple[List[ProductData], int]:
        """
        List products from storage with optional filtering and pagination.
        
        Args:
            filters: Optional dictionary of filter criteria
            limit: Maximum number of products to return
            offset: Number of products to skip
            sort_by: Field to sort by
            sort_order: Sort order ("asc" or "desc")
            
        Returns:
            Tuple[List[ProductData], int]: List of products and total count
            
        Raises:
            StorageError: If there's an error listing products
        """
        try:
            # Load the index
            index = await self._load_index()
            
            # Apply filters if any
            filtered_ids = []
            for product_id, metadata in index.items():
                if self._matches_filters(metadata, filters):
                    filtered_ids.append(product_id)
                    
            # Apply sorting
            if sort_by is not None and sort_by in ["title", "brand", "saved_at", "updated_at"]:
                filtered_ids.sort(
                    key=lambda pid: index[pid].get(sort_by, ""),
                    reverse=(sort_order.lower() == "desc")
                )
                
            # Apply pagination
            paginated_ids = filtered_ids[offset:offset + limit]
            
            # Load the products
            products = []
            for product_id in paginated_ids:
                try:
                    product = await self.get_product(product_id)
                    products.append(product)
                except (ProductNotFoundError, StorageError) as e:
                    logger.warning(f"Failed to load product {product_id}: {e}")
                    continue
                    
            return products, len(filtered_ids)
            
        except Exception as e:
            logger.error(f"Failed to list products: {e}")
            raise StorageError(f"Failed to list products: {e}")
    
    def _matches_filters(self, metadata: Dict[str, Any], filters: Optional[Dict[str, Any]]) -> bool:
        """
        Check if a product matches the given filters.
        
        Args:
            metadata: The product metadata
            filters: The filters to apply
            
        Returns:
            bool: True if the product matches the filters, False otherwise
        """
        if not filters:
            return True
            
        for key, value in filters.items():
            # Skip if key doesn't exist in metadata
            if key not in metadata:
                return False
                
            # Handle different types of filter values
            if isinstance(value, str):
                # For strings, do case-insensitive substring matching
                if isinstance(metadata[key], str):
                    if value.lower() not in metadata[key].lower():
                        return False
                else:
                    # If metadata value is not a string but filter is, convert to string for comparison
                    if value.lower() not in str(metadata[key]).lower():
                        return False
            elif isinstance(value, list):
                # For lists, check if any value in the list matches
                if not any(self._matches_single_value(metadata[key], v) for v in value):
                    return False
            elif isinstance(value, dict):
                # For nested dictionaries
                if not isinstance(metadata[key], dict):
                    return False
                if not self._matches_filters(metadata[key], value):
                    return False
            else:
                # For other types (numbers, booleans), do exact matching
                if metadata[key] != value:
                    return False
                
        return True
        
    def _matches_single_value(self, metadata_value: Any, filter_value: Any) -> bool:
        """
        Check if a single metadata value matches a filter value.
        
        Args:
            metadata_value: The value from the metadata
            filter_value: The value from the filter
            
        Returns:
            bool: True if the values match, False otherwise
        """
        if isinstance(filter_value, str) and isinstance(metadata_value, str):
            return filter_value.lower() in metadata_value.lower()
        elif isinstance(metadata_value, list):
            return filter_value in metadata_value
        else:
            return metadata_value == filter_value 