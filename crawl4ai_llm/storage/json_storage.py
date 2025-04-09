"""
JSON file-based storage implementation.

This module provides a storage implementation that uses JSON files to store
and retrieve product data, with an index file for efficient lookups.
"""

import asyncio
import json
import os
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union, Set
import aiofiles
import aiofiles.os
from filelock import FileLock

from ..models import ProductData
from .base import (
    BaseStorage,
    ProductNotFoundError,
    DuplicateProductError,
    StorageConnectionError
)

logger = logging.getLogger(__name__)


class JSONStorage(BaseStorage):
    """
    A storage implementation that uses JSON files to store product data.
    
    This implementation stores each product in a separate JSON file and 
    maintains an index file for efficient lookups, including batch operations.
    
    The index file keeps track of product IDs, URLs, and other metadata for
    filtering and sorting operations.
    
    Attributes:
        directory: Path to the directory for storing the JSON files.
        lock_timeout: Timeout for file lock in seconds.
    """
    
    def __init__(self, directory: str, lock_timeout: int = 30):
        """
        Initialize the JSON storage.
        
        Args:
            directory: Path to the directory for storing JSON files.
            lock_timeout: Timeout for file lock in seconds.
            
        Raises:
            StorageConnectionError: If the directory doesn't exist or is not writable.
        """
        self.directory = directory
        self.lock_timeout = lock_timeout
        self.index_path = os.path.join(directory, "index.json")
        self.lock_path = os.path.join(directory, "index.lock")
        
        # Create the directory if it doesn't exist
        try:
            os.makedirs(directory, exist_ok=True)
            
            # Test if we can write to the directory
            test_file = os.path.join(directory, ".test_write")
            with open(test_file, "w") as f:
                f.write("")
            os.remove(test_file)
            
        except (PermissionError, OSError) as e:
            raise StorageConnectionError(f"Cannot access storage directory: {e}")
    
    async def _get_product_id(self, product: ProductData) -> str:
        """
        Generate a product ID based on its attributes.
        
        Args:
            product: The product data.
            
        Returns:
            str: The generated product ID.
        """
        # Use the product's ID if it already has one
        if product.id:
            return product.id
        
        # Otherwise, generate an ID based on the product URL
        if product.url:
            return hashlib.md5(product.url.encode()).hexdigest()
        
        # If neither ID nor URL is available, use a combination of title, brand, and SKU
        id_components = []
        if product.title:
            id_components.append(product.title)
        if product.brand:
            id_components.append(product.brand)
        if product.identifiers:
            for key, value in product.identifiers.items():
                id_components.append(f"{key}:{value}")
        
        if id_components:
            id_string = "_".join(id_components)
            return hashlib.md5(id_string.encode()).hexdigest()
        
        # Last resort: timestamp + part of the product's hash
        timestamp = datetime.now().isoformat()
        product_hash = hash(product.json())
        return hashlib.md5(f"{timestamp}_{product_hash}".encode()).hexdigest()
    
    def _get_file_path(self, product_id: str) -> str:
        """
        Get the file path for a product.
        
        Args:
            product_id: The ID of the product.
            
        Returns:
            str: The file path.
        """
        return os.path.join(self.directory, f"{product_id}.json")
    
    async def _load_index(self) -> Dict[str, Dict[str, Any]]:
        """
        Load the index file.
        
        Returns:
            Dict[str, Dict[str, Any]]: The index data.
            
        Raises:
            StorageConnectionError: If there's an error loading the index.
        """
        try:
            if await aiofiles.os.path.exists(self.index_path):
                async with aiofiles.open(self.index_path, "r") as f:
                    content = await f.read()
                    return json.loads(content) if content else {}
            return {}
        except (json.JSONDecodeError, PermissionError, OSError) as e:
            logger.error(f"Error loading index: {e}")
            return {}
    
    async def _save_index(self, index: Dict[str, Dict[str, Any]]) -> None:
        """
        Save the index file.
        
        Args:
            index: The index data to save.
            
        Raises:
            StorageConnectionError: If there's an error saving the index.
        """
        try:
            lock = FileLock(self.lock_path, timeout=self.lock_timeout)
            with lock:
                async with aiofiles.open(self.index_path, "w") as f:
                    await f.write(json.dumps(index, indent=2))
        except (PermissionError, OSError, json.JSONDecodeError) as e:
            logger.error(f"Error saving index: {e}")
            raise StorageConnectionError(f"Cannot save index: {e}")
    
    async def save_product(self, product: ProductData) -> str:
        """
        Save a single product to storage.
        
        Args:
            product: The product data to save.
            
        Returns:
            str: The ID of the saved product.
            
        Raises:
            DuplicateProductError: If the product already exists.
            StorageConnectionError: If there's an error connecting to storage.
        """
        # Generate or use the product ID
        product_id = await self._get_product_id(product)
        file_path = self._get_file_path(product_id)
        
        # Check if the product already exists
        if await aiofiles.os.path.exists(file_path):
            raise DuplicateProductError(f"Product with ID {product_id} already exists")
        
        # Set the product ID
        product_dict = product.dict()
        product_dict["id"] = product_id
        product = ProductData(**product_dict)
        
        # Save the product file
        try:
            async with aiofiles.open(file_path, "w") as f:
                await f.write(product.json(indent=2))
        except (PermissionError, OSError) as e:
            logger.error(f"Error saving product {product_id}: {e}")
            raise StorageConnectionError(f"Cannot save product: {e}")
        
        # Update the index
        try:
            lock = FileLock(self.lock_path, timeout=self.lock_timeout)
            with lock:
                index = await self._load_index()
                
                # Create index entry with metadata for efficient filtering
                index[product_id] = {
                    "id": product_id,
                    "url": product.url,
                    "title": product.title,
                    "brand": product.brand,
                    "price": product.price.amount if product.price else None,
                    "currency": product.price.currency if product.price else None,
                    "identifiers": product.identifiers,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                
                await self._save_index(index)
        except Exception as e:
            # If index update fails, remove the product file
            logger.error(f"Error updating index for product {product_id}: {e}")
            try:
                await aiofiles.os.remove(file_path)
            except Exception:
                pass
            raise StorageConnectionError(f"Cannot update index: {e}")
        
        return product_id
    
    async def save_products(self, products: List[ProductData]) -> List[str]:
        """
        Save multiple products to storage in batch.
        
        Args:
            products: List of product data to save.
            
        Returns:
            List[str]: The IDs of the saved products.
            
        Raises:
            DuplicateProductError: If any product already exists.
            StorageConnectionError: If there's an error connecting to storage.
        """
        if not products:
            return []
        
        product_ids = []
        saved_files = []
        index = await self._load_index()
        index_updated = False
        
        try:
            # Process each product
            for product in products:
                product_id = await self._get_product_id(product)
                file_path = self._get_file_path(product_id)
                
                # Check if the product already exists
                if await aiofiles.os.path.exists(file_path):
                    # Clean up any files we've created
                    for path in saved_files:
                        try:
                            await aiofiles.os.remove(path)
                        except Exception:
                            pass
                    raise DuplicateProductError(f"Product with ID {product_id} already exists")
                
                # Set the product ID
                product_dict = product.dict()
                product_dict["id"] = product_id
                product = ProductData(**product_dict)
                
                # Save the product file
                async with aiofiles.open(file_path, "w") as f:
                    await f.write(product.json(indent=2))
                
                saved_files.append(file_path)
                product_ids.append(product_id)
                
                # Update index entry
                now = datetime.now().isoformat()
                index[product_id] = {
                    "id": product_id,
                    "url": product.url,
                    "title": product.title,
                    "brand": product.brand,
                    "price": product.price.amount if product.price else None,
                    "currency": product.price.currency if product.price else None,
                    "identifiers": product.identifiers,
                    "created_at": now,
                    "updated_at": now
                }
                index_updated = True
            
            # Save the updated index
            if index_updated:
                lock = FileLock(self.lock_path, timeout=self.lock_timeout)
                with lock:
                    await self._save_index(index)
            
            return product_ids
        
        except (PermissionError, OSError) as e:
            # Clean up any files we've created
            for path in saved_files:
                try:
                    await aiofiles.os.remove(path)
                except Exception:
                    pass
            
            logger.error(f"Error saving products: {e}")
            raise StorageConnectionError(f"Cannot save products: {e}")
    
    async def get_product(self, product_id: str) -> ProductData:
        """
        Retrieve a product by ID.
        
        Args:
            product_id: The ID of the product to retrieve.
            
        Returns:
            ProductData: The product data.
            
        Raises:
            ProductNotFoundError: If the product doesn't exist.
            StorageConnectionError: If there's an error connecting to storage.
        """
        file_path = self._get_file_path(product_id)
        
        try:
            if not await aiofiles.os.path.exists(file_path):
                raise ProductNotFoundError(f"Product with ID {product_id} not found")
            
            async with aiofiles.open(file_path, "r") as f:
                content = await f.read()
                return ProductData.parse_raw(content)
        
        except ProductNotFoundError:
            raise
        except (json.JSONDecodeError, PermissionError, OSError) as e:
            logger.error(f"Error loading product {product_id}: {e}")
            raise StorageConnectionError(f"Cannot load product: {e}")
    
    async def get_products(self, product_ids: List[str]) -> List[ProductData]:
        """
        Retrieve multiple products by their IDs.
        
        Args:
            product_ids: List of product IDs to retrieve.
            
        Returns:
            List[ProductData]: The retrieved products.
            
        Note:
            This method will not raise ProductNotFoundError if some products
            don't exist. It will simply return the products that were found.
            
        Raises:
            StorageConnectionError: If there's an error connecting to storage.
        """
        if not product_ids:
            return []
        
        results = []
        
        # Create tasks for each product retrieval
        tasks = []
        for product_id in product_ids:
            tasks.append(self._get_product_with_suppressed_error(product_id))
        
        # Execute all tasks concurrently
        products = await asyncio.gather(*tasks)
        
        # Filter out None values (products that weren't found)
        return [p for p in products if p is not None]
    
    async def _get_product_with_suppressed_error(self, product_id: str) -> Optional[ProductData]:
        """
        Retrieve a product by ID, suppressing ProductNotFoundError.
        
        Args:
            product_id: The ID of the product to retrieve.
            
        Returns:
            Optional[ProductData]: The product data, or None if not found.
            
        Raises:
            StorageConnectionError: If there's an error connecting to storage.
        """
        try:
            return await self.get_product(product_id)
        except ProductNotFoundError:
            return None
    
    async def update_product(self, product_id: str, product: ProductData) -> bool:
        """
        Update an existing product.
        
        Args:
            product_id: The ID of the product to update.
            product: The new product data.
            
        Returns:
            bool: True if the update was successful.
            
        Raises:
            ProductNotFoundError: If the product doesn't exist.
            StorageConnectionError: If there's an error connecting to storage.
        """
        file_path = self._get_file_path(product_id)
        
        # Check if the product exists
        if not await aiofiles.os.path.exists(file_path):
            raise ProductNotFoundError(f"Product with ID {product_id} not found")
        
        # Set the product ID to ensure consistency
        product_dict = product.dict()
        product_dict["id"] = product_id
        product = ProductData(**product_dict)
        
        # Save the updated product
        try:
            async with aiofiles.open(file_path, "w") as f:
                await f.write(product.json(indent=2))
        except (PermissionError, OSError) as e:
            logger.error(f"Error updating product {product_id}: {e}")
            raise StorageConnectionError(f"Cannot update product: {e}")
        
        # Update the index
        try:
            lock = FileLock(self.lock_path, timeout=self.lock_timeout)
            with lock:
                index = await self._load_index()
                
                if product_id in index:
                    index[product_id].update({
                        "url": product.url,
                        "title": product.title,
                        "brand": product.brand,
                        "price": product.price.amount if product.price else None,
                        "currency": product.price.currency if product.price else None,
                        "identifiers": product.identifiers,
                        "updated_at": datetime.now().isoformat()
                    })
                    
                    await self._save_index(index)
        except Exception as e:
            logger.error(f"Error updating index for product {product_id}: {e}")
            # We don't raise an exception here because the product file has been updated
        
        return True
    
    async def update_products(self, products: Dict[str, ProductData]) -> Dict[str, bool]:
        """
        Update multiple products in batch.
        
        Args:
            products: Dictionary mapping product IDs to new product data.
            
        Returns:
            Dict[str, bool]: Dictionary mapping product IDs to success status.
            
        Raises:
            StorageConnectionError: If there's an error connecting to storage.
        """
        if not products:
            return {}
        
        results = {}
        index = await self._load_index()
        index_updated = False
        
        # Process each product
        for product_id, product in products.items():
            file_path = self._get_file_path(product_id)
            
            # Check if the product exists
            if not await aiofiles.os.path.exists(file_path):
                results[product_id] = False
                continue
            
            # Set the product ID to ensure consistency
            product_dict = product.dict()
            product_dict["id"] = product_id
            product = ProductData(**product_dict)
            
            try:
                # Save the updated product
                async with aiofiles.open(file_path, "w") as f:
                    await f.write(product.json(indent=2))
                
                # Update index entry
                if product_id in index:
                    index[product_id].update({
                        "url": product.url,
                        "title": product.title,
                        "brand": product.brand,
                        "price": product.price.amount if product.price else None,
                        "currency": product.price.currency if product.price else None,
                        "identifiers": product.identifiers,
                        "updated_at": datetime.now().isoformat()
                    })
                    index_updated = True
                
                results[product_id] = True
            
            except Exception as e:
                logger.error(f"Error updating product {product_id}: {e}")
                results[product_id] = False
        
        # Save the updated index
        if index_updated:
            try:
                lock = FileLock(self.lock_path, timeout=self.lock_timeout)
                with lock:
                    await self._save_index(index)
            except Exception as e:
                logger.error(f"Error updating index: {e}")
                # We don't raise an exception here because some products may have been updated
        
        return results
    
    async def delete_product(self, product_id: str) -> bool:
        """
        Delete a product.
        
        Args:
            product_id: The ID of the product to delete.
            
        Returns:
            bool: True if the deletion was successful.
            
        Raises:
            ProductNotFoundError: If the product doesn't exist.
            StorageConnectionError: If there's an error connecting to storage.
        """
        file_path = self._get_file_path(product_id)
        
        # Check if the product exists
        if not await aiofiles.os.path.exists(file_path):
            raise ProductNotFoundError(f"Product with ID {product_id} not found")
        
        # Delete the product file
        try:
            await aiofiles.os.remove(file_path)
        except (PermissionError, OSError) as e:
            logger.error(f"Error deleting product {product_id}: {e}")
            raise StorageConnectionError(f"Cannot delete product: {e}")
        
        # Update the index
        try:
            lock = FileLock(self.lock_path, timeout=self.lock_timeout)
            with lock:
                index = await self._load_index()
                
                if product_id in index:
                    del index[product_id]
                    await self._save_index(index)
        except Exception as e:
            logger.error(f"Error updating index after deletion: {e}")
            # We don't raise an exception here because the product file has been deleted
        
        return True
    
    async def delete_products(self, product_ids: List[str]) -> Dict[str, bool]:
        """
        Delete multiple products in batch.
        
        Args:
            product_ids: List of product IDs to delete.
            
        Returns:
            Dict[str, bool]: Dictionary mapping product IDs to success status.
            
        Raises:
            StorageConnectionError: If there's an error connecting to storage.
        """
        if not product_ids:
            return {}
        
        results = {}
        index = await self._load_index()
        index_updated = False
        
        # Process each product
        for product_id in product_ids:
            file_path = self._get_file_path(product_id)
            
            # Check if the product exists
            if not await aiofiles.os.path.exists(file_path):
                results[product_id] = False
                continue
            
            try:
                # Delete the product file
                await aiofiles.os.remove(file_path)
                
                # Update index
                if product_id in index:
                    del index[product_id]
                    index_updated = True
                
                results[product_id] = True
            
            except Exception as e:
                logger.error(f"Error deleting product {product_id}: {e}")
                results[product_id] = False
        
        # Save the updated index
        if index_updated:
            try:
                lock = FileLock(self.lock_path, timeout=self.lock_timeout)
                with lock:
                    await self._save_index(index)
            except Exception as e:
                logger.error(f"Error updating index after deletion: {e}")
                # We don't raise an exception here because some products may have been deleted
        
        return results
    
    async def list_products(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = "asc"
    ) -> Tuple[List[ProductData], int]:
        """
        List products with optional filtering, pagination, and sorting.
        
        Args:
            filters: Dictionary mapping fields to filter values.
            limit: Maximum number of products to return.
            offset: Number of products to skip.
            sort_by: Field to sort by.
            sort_order: Sort order, "asc" or "desc".
            
        Returns:
            Tuple[List[ProductData], int]: List of products and total count.
            
        Raises:
            StorageConnectionError: If there's an error connecting to storage.
        """
        try:
            # Load the index
            index = await self._load_index()
            
            # Apply filters
            if filters:
                filtered_ids = []
                for product_id, metadata in index.items():
                    if await self._matches_filters(metadata, filters):
                        filtered_ids.append(product_id)
            else:
                filtered_ids = list(index.keys())
            
            # Apply sorting
            if sort_by:
                try:
                    # Sort by the specified field
                    sorted_ids = sorted(
                        filtered_ids,
                        key=lambda id_: index.get(id_, {}).get(sort_by, ""),
                        reverse=(sort_order.lower() == "desc")
                    )
                except (KeyError, TypeError):
                    # Fallback to sorting by ID
                    sorted_ids = sorted(
                        filtered_ids,
                        reverse=(sort_order.lower() == "desc")
                    )
            else:
                # Default sort by ID
                sorted_ids = sorted(filtered_ids)
            
            # Apply pagination
            total_count = len(sorted_ids)
            if offset is not None:
                sorted_ids = sorted_ids[offset:]
            if limit is not None:
                sorted_ids = sorted_ids[:limit]
            
            # Retrieve the products
            products = await self.get_products(sorted_ids)
            
            return products, total_count
        
        except (PermissionError, OSError, json.JSONDecodeError) as e:
            logger.error(f"Error listing products: {e}")
            raise StorageConnectionError(f"Cannot list products: {e}")
    
    async def _matches_filters(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """
        Check if the product's metadata matches the given filters.
        
        Args:
            metadata: The product metadata from the index.
            filters: Dictionary mapping fields to filter values.
            
        Returns:
            bool: True if the metadata matches the filters.
        """
        for field, value in filters.items():
            # Handle nested fields
            if "." in field:
                parts = field.split(".")
                field_value = metadata
                for part in parts:
                    if isinstance(field_value, dict) and part in field_value:
                        field_value = field_value[part]
                    else:
                        field_value = None
                        break
            else:
                field_value = metadata.get(field)
            
            # Handle different filter types
            if isinstance(value, dict):
                # Range filter
                if "min" in value and field_value is not None:
                    if field_value < value["min"]:
                        return False
                if "max" in value and field_value is not None:
                    if field_value > value["max"]:
                        return False
            elif isinstance(value, list):
                # Multiple value filter
                if field_value not in value:
                    return False
            elif field_value != value:
                # Exact match filter
                return False
        
        return True