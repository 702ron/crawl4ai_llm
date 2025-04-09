"""
JSON file-based storage implementation.

This module provides a storage implementation that uses JSON files
to store product data on the filesystem.
"""

import os
import json
import asyncio
import logging
import uuid
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set, Sequence
from datetime import datetime
import aiofiles
import aiofiles.os
from filelock import FileLock

from ..config import StorageConfig
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
    Storage implementation using JSON files.
    
    This class provides a storage implementation that uses JSON files to store
    product data on the filesystem. It maintains an index file for quick lookups
    and efficient filtering.
    
    Attributes:
        config: Storage configuration
        storage_path: Path to the storage directory
        index_path: Path to the index file
        locks: Dictionary of file locks
    """
    
    def __init__(self, config: StorageConfig):
        """
        Initialize JSON storage.
        
        Args:
            config: Storage configuration
            
        Raises:
            StorageConnectionError: If there's an issue creating/accessing the storage directory
        """
        self.config = config
        self.storage_path = Path(config.path)
        self.index_path = self.storage_path / "index.json"
        self.locks: Dict[str, FileLock] = {}
        
        try:
            # Create storage directory if it doesn't exist and create_if_missing is True
            if config.create_if_missing and not self.storage_path.exists():
                self.storage_path.mkdir(parents=True, exist_ok=True)
                
            # Check if storage directory is writable
            if not os.access(self.storage_path, os.W_OK):
                raise StorageConnectionError(
                    f"Storage directory {self.storage_path} is not writable"
                )
        except (PermissionError, OSError) as e:
            raise StorageConnectionError(f"Error accessing storage directory: {str(e)}")
    
    def _get_product_id(self, product_data: ProductData) -> str:
        """
        Generate a product ID based on product data.
        
        If use_uuid is True, generates a UUID. Otherwise, tries to create an ID
        from product attributes like URL, title, and brand.
        
        Args:
            product_data: Product data
            
        Returns:
            Product ID string
        """
        if self.config.use_uuid:
            return str(uuid.uuid4())
        
        # Try to create a deterministic ID based on product attributes
        if product_data.identifiers:
            # Use an identifier (SKU, UPC, etc.) if available
            for id_type in ["sku", "upc", "ean", "isbn", "mpn", "gtin"]:
                if id_type in product_data.identifiers:
                    return f"{id_type}_{product_data.identifiers[id_type]}"
        
        # Fallback to URL-based ID
        url_path = str(product_data.url).split("/")[-1]
        if "?" in url_path:
            url_path = url_path.split("?")[0]
        
        if url_path and not url_path.isspace():
            return re.sub(r'[^\w\-_]', '_', url_path.lower())
        
        # Last resort: hash of URL and title
        hash_input = f"{product_data.url}_{product_data.title}"
        return str(abs(hash(hash_input)) % 100000000)
    
    def _get_file_path(self, product_id: str) -> Path:
        """
        Get the file path for a product ID.
        
        Args:
            product_id: Product ID
            
        Returns:
            Path object for the product file
        """
        # Sanitize product ID to create a safe filename
        safe_id = re.sub(r'[^\w\-_]', '_', product_id)
        return self.storage_path / f"{safe_id}.json"
    
    def _get_lock(self, file_path: Path) -> FileLock:
        """
        Get or create a file lock for the specified path.
        
        Args:
            file_path: Path to lock
            
        Returns:
            FileLock object
        """
        path_str = str(file_path)
        if path_str not in self.locks:
            self.locks[path_str] = FileLock(f"{path_str}.lock", timeout=self.config.lock_timeout)
        
        return self.locks[path_str]
    
    async def _load_index(self) -> Dict[str, Dict[str, Any]]:
        """
        Load the index file.
        
        Returns:
            Dictionary mapping product IDs to index entries
        """
        if not self.index_path.exists():
            return {}
        
        try:
            async with self._get_lock(self.index_path):
                async with aiofiles.open(self.index_path, "r") as f:
                    content = await f.read()
                    return json.loads(content) if content else {}
        except (json.JSONDecodeError, FileNotFoundError):
            logger.warning(f"Index file {self.index_path} is corrupted or missing, creating a new one")
            return {}
        except Exception as e:
            logger.error(f"Error loading index: {str(e)}")
            return {}
    
    async def _save_index(self, index: Dict[str, Dict[str, Any]]) -> None:
        """
        Save the index file.
        
        Args:
            index: Dictionary mapping product IDs to index entries
        """
        try:
            async with self._get_lock(self.index_path):
                async with aiofiles.open(self.index_path, "w") as f:
                    await f.write(json.dumps(index, indent=2))
        except (PermissionError, OSError) as e:
            logger.error(f"Error saving index: {str(e)}")
            raise StorageConnectionError(f"Error saving index: {str(e)}")
    
    def _create_index_entry(self, product_id: str, product_data: ProductData) -> Dict[str, Any]:
        """
        Create an index entry for a product.
        
        Args:
            product_id: Product ID
            product_data: Product data
            
        Returns:
            Dictionary containing index entry
        """
        return {
            "id": product_id,
            "url": str(product_data.url),
            "title": product_data.title,
            "brand": product_data.brand,
            "available": product_data.available,
            "extracted_at": product_data.extracted_at.isoformat() 
                if product_data.extracted_at else None,
            "identifiers": product_data.identifiers,
            # Add price info to index for sorting/filtering
            "price_info": [{
                "amount": p.amount,
                "currency": p.currency
            } for p in product_data.prices] if product_data.prices else []
        }
    
    async def save_product(self, product_data: ProductData) -> str:
        """
        Save product data to a JSON file.
        
        Args:
            product_data: Product data to save
            
        Returns:
            Product ID
            
        Raises:
            DuplicateProductError: If the product already exists
            StorageConnectionError: If there's an issue saving the product
        """
        # Generate product ID
        product_id = self._get_product_id(product_data)
        file_path = self._get_file_path(product_id)
        
        # Check if product already exists
        if file_path.exists():
            raise DuplicateProductError(f"Product with ID {product_id} already exists")
        
        try:
            # Create index entry
            index = await self._load_index()
            
            # Add basic metadata to the index for searching
            index_entry = self._create_index_entry(product_id, product_data)
            
            # Update the index
            index[product_id] = index_entry
            await self._save_index(index)
            
            # Save the product data
            async with self._get_lock(file_path):
                async with aiofiles.open(file_path, "w") as f:
                    await f.write(product_data.model_dump_json(indent=2))
            
            return product_id
            
        except (PermissionError, OSError) as e:
            logger.error(f"Error saving product: {str(e)}")
            raise StorageConnectionError(f"Error saving product: {str(e)}")
    
    async def save_products(self, products: Sequence[ProductData]) -> List[str]:
        """
        Save multiple products in a single batch operation.
        
        This optimized implementation reduces the number of index file operations
        by updating the index once for all products.
        
        Args:
            products: Sequence of ProductData objects
            
        Returns:
            List of product IDs for successfully saved products
        """
        if not products:
            return []
        
        product_ids = []
        index = await self._load_index()
        index_updated = False
        
        for product in products:
            try:
                # Generate product ID
                product_id = self._get_product_id(product)
                file_path = self._get_file_path(product_id)
                
                # Check if product already exists
                if file_path.exists():
                    logger.warning(f"Product with ID {product_id} already exists, skipping")
                    continue
                
                # Add to index
                index_entry = self._create_index_entry(product_id, product)
                index[product_id] = index_entry
                index_updated = True
                
                # Save product file
                async with self._get_lock(file_path):
                    async with aiofiles.open(file_path, "w") as f:
                        await f.write(product.model_dump_json(indent=2))
                
                product_ids.append(product_id)
                
            except Exception as e:
                logger.error(f"Error saving product: {str(e)}")
        
        # Save index once if any products were added
        if index_updated:
            await self._save_index(index)
        
        return product_ids
    
    async def get_product(self, product_id: str) -> ProductData:
        """
        Retrieve product data by ID.
        
        Args:
            product_id: Product ID
            
        Returns:
            Product data
            
        Raises:
            ProductNotFoundError: If the product is not found
            StorageError: If there's an issue reading the product
        """
        file_path = self._get_file_path(product_id)
        
        if not file_path.exists():
            raise ProductNotFoundError(f"Product with ID {product_id} not found")
        
        try:
            async with self._get_lock(file_path):
                async with aiofiles.open(file_path, "r") as f:
                    content = await f.read()
                    return ProductData.model_validate_json(content)
        except json.JSONDecodeError:
            logger.error(f"Product file {file_path} is corrupted")
            raise StorageError(f"Product file {file_path} is corrupted")
        except Exception as e:
            logger.error(f"Error reading product: {str(e)}")
            raise StorageError(f"Error reading product: {str(e)}")
    
    async def get_products(self, product_ids: Sequence[str]) -> List[ProductData]:
        """
        Retrieve multiple products by ID.
        
        This implementation uses asyncio.gather to load products concurrently.
        
        Args:
            product_ids: Sequence of product IDs
            
        Returns:
            List of ProductData objects for found products
        """
        if not product_ids:
            return []
        
        async def get_product_safe(pid: str) -> Optional[ProductData]:
            try:
                return await self.get_product(pid)
            except (ProductNotFoundError, StorageError) as e:
                logger.warning(f"Error loading product {pid}: {str(e)}")
                return None
        
        # Load products concurrently
        results = await asyncio.gather(*[get_product_safe(pid) for pid in product_ids])
        
        # Filter out None results (failed loads)
        return [p for p in results if p is not None]
    
    async def update_product(self, product_id: str, product_data: ProductData) -> bool:
        """
        Update existing product data.
        
        Args:
            product_id: Product ID
            product_data: Updated product data
            
        Returns:
            True if successful
            
        Raises:
            ProductNotFoundError: If the product is not found
            StorageConnectionError: If there's an issue updating the product
        """
        file_path = self._get_file_path(product_id)
        
        if not file_path.exists():
            raise ProductNotFoundError(f"Product with ID {product_id} not found")
        
        try:
            # Update the product file
            async with self._get_lock(file_path):
                async with aiofiles.open(file_path, "w") as f:
                    await f.write(product_data.model_dump_json(indent=2))
            
            # Update the index
            index = await self._load_index()
            if product_id in index:
                index[product_id].update({
                    "url": str(product_data.url),
                    "title": product_data.title,
                    "brand": product_data.brand,
                    "available": product_data.available,
                    "extracted_at": product_data.extracted_at.isoformat() 
                        if product_data.extracted_at else None,
                    "identifiers": product_data.identifiers,
                    "price_info": [{
                        "amount": p.amount,
                        "currency": p.currency
                    } for p in product_data.prices] if product_data.prices else []
                })
                await self._save_index(index)
            
            return True
            
        except (PermissionError, OSError) as e:
            logger.error(f"Error updating product: {str(e)}")
            raise StorageConnectionError(f"Error updating product: {str(e)}")
    
    async def update_products(self, products: Dict[str, ProductData]) -> Dict[str, bool]:
        """
        Update multiple products in a single batch operation.
        
        This optimized implementation reduces the number of index file operations
        by updating the index once for all products.
        
        Args:
            products: Dictionary mapping product IDs to updated ProductData objects
            
        Returns:
            Dictionary mapping product IDs to update success (True/False)
        """
        if not products:
            return {}
        
        results = {}
        index = await self._load_index()
        index_updated = False
        
        for product_id, product_data in products.items():
            try:
                file_path = self._get_file_path(product_id)
                
                if not file_path.exists():
                    logger.warning(f"Product with ID {product_id} not found, skipping")
                    results[product_id] = False
                    continue
                
                # Update product file
                async with self._get_lock(file_path):
                    async with aiofiles.open(file_path, "w") as f:
                        await f.write(product_data.model_dump_json(indent=2))
                
                # Update index
                if product_id in index:
                    index[product_id].update({
                        "url": str(product_data.url),
                        "title": product_data.title,
                        "brand": product_data.brand,
                        "available": product_data.available,
                        "extracted_at": product_data.extracted_at.isoformat() 
                            if product_data.extracted_at else None,
                        "identifiers": product_data.identifiers,
                        "price_info": [{
                            "amount": p.amount,
                            "currency": p.currency
                        } for p in product_data.prices] if product_data.prices else []
                    })
                    index_updated = True
                
                results[product_id] = True
                
            except Exception as e:
                logger.error(f"Error updating product {product_id}: {str(e)}")
                results[product_id] = False
        
        # Save index once if any products were updated
        if index_updated:
            await self._save_index(index)
        
        return results
    
    async def delete_product(self, product_id: str) -> bool:
        """
        Delete a product from storage.
        
        Args:
            product_id: Product ID
            
        Returns:
            True if successful
            
        Raises:
            ProductNotFoundError: If the product is not found
            StorageConnectionError: If there's an issue deleting the product
        """
        file_path = self._get_file_path(product_id)
        
        if not file_path.exists():
            raise ProductNotFoundError(f"Product with ID {product_id} not found")
        
        try:
            # Delete the product file
            async with self._get_lock(file_path):
                await aiofiles.os.remove(file_path)
            
            # Update the index
            index = await self._load_index()
            if product_id in index:
                del index[product_id]
                await self._save_index(index)
            
            # Remove the lock
            path_str = str(file_path)
            if path_str in self.locks:
                del self.locks[path_str]
            
            return True
            
        except (PermissionError, OSError) as e:
            logger.error(f"Error deleting product: {str(e)}")
            raise StorageConnectionError(f"Error deleting product: {str(e)}")
    
    async def delete_products(self, product_ids: Sequence[str]) -> Dict[str, bool]:
        """
        Delete multiple products in a single batch operation.
        
        This optimized implementation reduces the number of index file operations
        by updating the index once for all products.
        
        Args:
            product_ids: Sequence of product IDs to delete
            
        Returns:
            Dictionary mapping product IDs to deletion success (True/False)
        """
        if not product_ids:
            return {}
        
        results = {}
        index = await self._load_index()
        index_updated = False
        
        for product_id in product_ids:
            try:
                file_path = self._get_file_path(product_id)
                
                if not file_path.exists():
                    logger.warning(f"Product with ID {product_id} not found, skipping")
                    results[product_id] = False
                    continue
                
                # Delete product file
                async with self._get_lock(file_path):
                    await aiofiles.os.remove(file_path)
                
                # Update index
                if product_id in index:
                    del index[product_id]
                    index_updated = True
                
                # Remove lock
                path_str = str(file_path)
                if path_str in self.locks:
                    del self.locks[path_str]
                
                results[product_id] = True
                
            except Exception as e:
                logger.error(f"Error deleting product {product_id}: {str(e)}")
                results[product_id] = False
        
        # Save index once if any products were deleted
        if index_updated:
            await self._save_index(index)
        
        return results
    
    async def list_products(self, 
                         filters: Optional[Dict[str, Any]] = None, 
                         limit: int = 100, 
                         offset: int = 0,
                         sort_by: Optional[str] = None,
                         sort_order: str = "asc") -> Tuple[List[ProductData], int]:
        """
        List products with optional filtering, pagination, and sorting.
        
        Args:
            filters: Optional dictionary of filters to apply
            limit: Maximum number of products to return
            offset: Number of products to skip
            sort_by: Field to sort by
            sort_order: Sort order ("asc" or "desc")
            
        Returns:
            Tuple of (products list, total count)
            
        Raises:
            StorageConnectionError: If there's an issue listing products
        """
        try:
            # Load the index
            index = await self._load_index()
            
            # Filter products
            if filters:
                product_ids = [pid for pid, data in index.items() 
                              if self._matches_filters(data, filters)]
            else:
                product_ids = list(index.keys())
            
            # Sort products
            if sort_by:
                if sort_by == "price":
                    # Special case for price sorting
                    # This sorts by the first price in the list
                    def price_key(pid):
                        price_info = index[pid].get("price_info", [])
                        if price_info:
                            try:
                                return float(price_info[0].get("amount", 0))
                            except (ValueError, TypeError):
                                return 0
                        return 0
                    
                    product_ids.sort(key=price_key, reverse=(sort_order.lower() == "desc"))
                else:
                    # General sorting by index field
                    def sort_key(pid):
                        if "." in sort_by:
                            # Handle nested fields (e.g., "price_info.amount")
                            parts = sort_by.split(".")
                            value = index[pid]
                            for part in parts:
                                if isinstance(value, dict) and part in value:
                                    value = value[part]
                                else:
                                    value = None
                                    break
                            return value or ""
                        else:
                            # Simple field
                            return index[pid].get(sort_by, "")
                    
                    product_ids.sort(key=sort_key, reverse=(sort_order.lower() == "desc"))
            
            # Apply pagination
            total_count = len(product_ids)
            paginated_ids = product_ids[offset:offset + limit]
            
            # Load product data using batch method
            products = await self.get_products(paginated_ids)
            
            return products, total_count
            
        except Exception as e:
            logger.error(f"Error listing products: {str(e)}")
            raise StorageConnectionError(f"Error listing products: {str(e)}")
    
    def _matches_filters(self, data: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """
        Check if product metadata matches filters.
        
        Args:
            data: Product metadata from the index
            filters: Dictionary of filters to apply
            
        Returns:
            True if the product matches all filters, False otherwise
        """
        for field, value in filters.items():
            if field not in data:
                return False
            
            field_value = data[field]
            
            # Handle different filter types
            if isinstance(value, (str, int, float, bool)):
                # Simple equality for primitive types
                if isinstance(field_value, str) and isinstance(value, str):
                    # Case-insensitive substring match for strings
                    if value.lower() not in field_value.lower():
                        return False
                elif field_value != value:
                    return False
            elif isinstance(value, list):
                # Check if any value in the list matches
                if not any(v == field_value for v in value):
                    return False
            elif isinstance(value, dict):
                # For nested filters (e.g., {"price": {"min": 10, "max": 100}})
                for subfield, subvalue in value.items():
                    if subfield == "min" and isinstance(field_value, (int, float)):
                        if field_value < subvalue:
                            return False
                    elif subfield == "max" and isinstance(field_value, (int, float)):
                        if field_value > subvalue:
                            return False
                    elif subfield == "contains" and isinstance(field_value, list):
                        if subvalue not in field_value:
                            return False
                    elif subfield == "regex" and isinstance(field_value, str):
                        if not re.search(subvalue, field_value):
                            return False
                    elif field_value != subvalue:
                        return False
            else:
                # Unsupported filter type
                return False
        
        return True