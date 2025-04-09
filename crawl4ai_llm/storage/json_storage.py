"""
JSON file-based storage implementation.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Set

from .base import (
    BaseStorage,
    StorageError,
    StorageConnectionError,
    ProductNotFoundError,
    DuplicateProductError,
)


class JSONStorage(BaseStorage):
    """
    Storage implementation that uses JSON files.
    
    Each product is stored in its own JSON file, and an index file is used
    for quick lookups and filtering.
    """

    def __init__(self, directory: str, use_file_locks: bool = True):
        """
        Initialize the JSON storage.
        
        Args:
            directory: Path to the directory where product data will be stored.
            use_file_locks: Whether to use file locks for concurrent operations.
                            Set to False for better performance when concurrent
                            access is not a concern.
        
        Raises:
            StorageConnectionError: If the directory doesn't exist or can't be accessed.
        """
        self.directory = os.path.abspath(directory)
        self.use_file_locks = use_file_locks
        self.index_path = os.path.join(self.directory, "index.json")
        self.lock = asyncio.Lock()
        
        # Create the directory if it doesn't exist
        try:
            os.makedirs(self.directory, exist_ok=True)
        except (OSError, PermissionError) as e:
            raise StorageConnectionError(f"Failed to create directory: {e}")
            
        # Initialize the index file if it doesn't exist
        if not os.path.exists(self.index_path):
            try:
                with open(self.index_path, "w") as f:
                    json.dump({}, f)
            except (OSError, PermissionError) as e:
                raise StorageConnectionError(f"Failed to create index file: {e}")

    def _get_product_id(self, product_data: Dict[str, Any]) -> str:
        """
        Generate or retrieve a unique ID for a product.
        
        The ID is generated based on the following hierarchy:
        1. If 'id' is present in the product data, use it.
        2. Otherwise, generate an ID based on SKU + store name if available.
        3. Otherwise, generate an ID based on URL if available.
        4. Otherwise, generate a random UUID.
        
        Args:
            product_data: Dictionary containing product data.
            
        Returns:
            str: A unique ID for the product.
        """
        # If an ID is already provided, use it
        if "id" in product_data:
            return str(product_data["id"])
        
        # Generate ID based on SKU + store name if available
        if "sku" in product_data and "store_name" in product_data:
            return f"{product_data['store_name']}_{product_data['sku']}"
        
        # Generate ID based on URL if available
        if "url" in product_data:
            return f"url_{hash(product_data['url'])}"
        
        # Generate a random UUID as a last resort
        return str(uuid.uuid4())

    def _get_file_path(self, product_id: str) -> str:
        """
        Get the file path for a product.
        
        Args:
            product_id: The ID of the product.
            
        Returns:
            str: The file path for the product.
        """
        return os.path.join(self.directory, f"{product_id}.json")

    async def _load_index(self) -> Dict[str, Dict[str, Any]]:
        """
        Load the product index from the index file.
        
        Returns:
            Dict[str, Dict[str, Any]]: The product index.
        
        Raises:
            StorageConnectionError: If the index file can't be loaded.
        """
        try:
            if self.use_file_locks:
                async with self.lock:
                    # Use blocking file I/O in a thread pool
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(
                        None, 
                        lambda: json.load(open(self.index_path, "r")) 
                              if os.path.exists(self.index_path) and os.path.getsize(self.index_path) > 0 
                              else {}
                    )
            else:
                # Use blocking file I/O in a thread pool
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None, 
                    lambda: json.load(open(self.index_path, "r")) 
                          if os.path.exists(self.index_path) and os.path.getsize(self.index_path) > 0 
                          else {}
                )
        except json.JSONDecodeError:
            # If the index file is corrupted, return an empty index
            return {}
        except (OSError, PermissionError) as e:
            raise StorageConnectionError(f"Failed to load index: {e}")

    async def _save_index(self, index: Dict[str, Dict[str, Any]]) -> None:
        """
        Save the product index to the index file.
        
        Args:
            index: The product index to save.
        
        Raises:
            StorageConnectionError: If the index file can't be saved.
        """
        try:
            if self.use_file_locks:
                async with self.lock:
                    # Use blocking file I/O in a thread pool
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None, 
                        lambda: json.dump(index, open(self.index_path, "w"))
                    )
            else:
                # Use blocking file I/O in a thread pool
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, 
                    lambda: json.dump(index, open(self.index_path, "w"))
                )
        except (OSError, PermissionError) as e:
            raise StorageConnectionError(f"Failed to save index: {e}")

    async def save_product(self, product_data: Dict[str, Any]) -> str:
        """
        Save a product to storage.
        
        Args:
            product_data: Dictionary containing product data.
        
        Returns:
            str: The ID of the saved product.
        
        Raises:
            DuplicateProductError: If a product with the same ID already exists.
            StorageConnectionError: If there's an error connecting to the storage.
        """
        # Generate a unique ID for the product
        product_id = self._get_product_id(product_data)
        
        # Add the ID to the product data
        product_data["id"] = product_id
        
        # Add metadata
        product_data["metadata"] = product_data.get("metadata", {})
        product_data["metadata"]["created_at"] = datetime.now().isoformat()
        product_data["metadata"]["updated_at"] = datetime.now().isoformat()
        
        # Check if the product already exists
        index = await self._load_index()
        if product_id in index:
            raise DuplicateProductError(f"Product with ID '{product_id}' already exists")
        
        # Save the product to a file
        file_path = self._get_file_path(product_id)
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, 
                lambda: json.dump(product_data, open(file_path, "w"))
            )
        except (OSError, PermissionError) as e:
            raise StorageConnectionError(f"Failed to save product: {e}")
        
        # Update the index
        index[product_id] = {
            "id": product_id,
            "metadata": product_data["metadata"],
        }
        
        # Add key fields to the index for filtering
        for field in ["sku", "url", "store_name", "title"]:
            if field in product_data:
                index[product_id][field] = product_data[field]
        
        await self._save_index(index)
        
        return product_id

    async def save_products(self, products_data: List[Dict[str, Any]]) -> List[str]:
        """
        Save multiple products to storage in a batch operation.
        
        Args:
            products_data: List of dictionaries containing product data.
        
        Returns:
            List[str]: The IDs of the saved products, in the same order as the input.
        
        Raises:
            DuplicateProductError: If a product with the same ID already exists.
            StorageConnectionError: If there's an error connecting to the storage.
        """
        if not products_data:
            return []
            
        # Generate unique IDs for all products and check for duplicates
        product_ids = []
        index = await self._load_index()
        existing_ids = set(index.keys())
        
        # Prepare products with IDs and metadata
        prepared_products = []
        
        for product_data in products_data:
            product_id = self._get_product_id(product_data)
            
            if product_id in existing_ids:
                raise DuplicateProductError(f"Product with ID '{product_id}' already exists")
                
            # Add the ID to the product data
            product_data_copy = product_data.copy()
            product_data_copy["id"] = product_id
            
            # Add metadata
            product_data_copy["metadata"] = product_data_copy.get("metadata", {})
            product_data_copy["metadata"]["created_at"] = datetime.now().isoformat()
            product_data_copy["metadata"]["updated_at"] = datetime.now().isoformat()
            
            product_ids.append(product_id)
            prepared_products.append(product_data_copy)
            
            # Update the index entry
            index[product_id] = {
                "id": product_id,
                "metadata": product_data_copy["metadata"],
            }
            
            # Add key fields to the index for filtering
            for field in ["sku", "url", "store_name", "title"]:
                if field in product_data_copy:
                    index[product_id][field] = product_data_copy[field]
        
        # Save all products to files
        try:
            loop = asyncio.get_event_loop()
            tasks = []
            
            for product_id, product_data in zip(product_ids, prepared_products):
                file_path = self._get_file_path(product_id)
                tasks.append(loop.run_in_executor(
                    None,
                    lambda p=product_data, f=file_path: json.dump(p, open(f, "w"))
                ))
                
            await asyncio.gather(*tasks)
        except (OSError, PermissionError) as e:
            raise StorageConnectionError(f"Failed to save products: {e}")
        
        # Update the index with all new products
        await self._save_index(index)
        
        return product_ids

    async def get_product(self, product_id: str) -> Dict[str, Any]:
        """
        Retrieve a product from storage by ID.
        
        Args:
            product_id: The ID of the product to retrieve.
        
        Returns:
            Dict[str, Any]: The product data.
        
        Raises:
            ProductNotFoundError: If the product is not found.
            StorageConnectionError: If there's an error connecting to the storage.
        """
        file_path = self._get_file_path(product_id)
        
        try:
            if not os.path.exists(file_path):
                raise ProductNotFoundError(f"Product with ID '{product_id}' not found")
                
            loop = asyncio.get_event_loop()
            product_data = await loop.run_in_executor(
                None, 
                lambda: json.load(open(file_path, "r"))
            )
            
            return product_data
        except json.JSONDecodeError as e:
            raise StorageError(f"Invalid JSON in product file: {e}")
        except (OSError, PermissionError) as e:
            raise StorageConnectionError(f"Failed to retrieve product: {e}")

    async def get_products(self, product_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Retrieve multiple products from storage by their IDs in a batch operation.
        
        Args:
            product_ids: List of product IDs to retrieve.
        
        Returns:
            List[Dict[str, Any]]: The product data for each requested ID, in the same order.
        
        Raises:
            ProductNotFoundError: If any of the products are not found.
            StorageConnectionError: If there's an error connecting to the storage.
        """
        if not product_ids:
            return []
            
        # Check which products exist
        missing_ids = []
        file_paths = {}
        
        for product_id in product_ids:
            file_path = self._get_file_path(product_id)
            if not os.path.exists(file_path):
                missing_ids.append(product_id)
            else:
                file_paths[product_id] = file_path
                
        if missing_ids:
            raise ProductNotFoundError(f"Products with IDs '{', '.join(missing_ids)}' not found")
            
        # Retrieve all products in parallel
        try:
            loop = asyncio.get_event_loop()
            tasks = []
            
            for product_id in product_ids:
                file_path = file_paths[product_id]
                tasks.append(loop.run_in_executor(
                    None,
                    lambda f=file_path: json.load(open(f, "r"))
                ))
                
            return await asyncio.gather(*tasks)
        except json.JSONDecodeError as e:
            raise StorageError(f"Invalid JSON in product file: {e}")
        except (OSError, PermissionError) as e:
            raise StorageConnectionError(f"Failed to retrieve products: {e}")

    async def update_product(self, product_data: Dict[str, Any]) -> str:
        """
        Update an existing product in storage.
        
        Args:
            product_data: Dictionary containing product data. Must include 'id' field.
        
        Returns:
            str: The ID of the updated product.
        
        Raises:
            ProductNotFoundError: If the product is not found.
            ValueError: If the product_data doesn't contain an 'id' field.
            StorageConnectionError: If there's an error connecting to the storage.
        """
        if "id" not in product_data:
            raise ValueError("Product data must include 'id' field")
            
        product_id = str(product_data["id"])
        index = await self._load_index()
        
        if product_id not in index:
            raise ProductNotFoundError(f"Product with ID '{product_id}' not found")
            
        # Get the existing product to merge with the updates
        existing_product = await self.get_product(product_id)
        
        # Update the product data
        updated_product = {**existing_product, **product_data}
        
        # Update metadata
        updated_product["metadata"] = updated_product.get("metadata", {})
        updated_product["metadata"]["updated_at"] = datetime.now().isoformat()
        
        # Save the updated product
        file_path = self._get_file_path(product_id)
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, 
                lambda: json.dump(updated_product, open(file_path, "w"))
            )
        except (OSError, PermissionError) as e:
            raise StorageConnectionError(f"Failed to update product: {e}")
        
        # Update the index
        index[product_id] = {
            "id": product_id,
            "metadata": updated_product["metadata"],
        }
        
        # Add key fields to the index for filtering
        for field in ["sku", "url", "store_name", "title"]:
            if field in updated_product:
                index[product_id][field] = updated_product[field]
        
        await self._save_index(index)
        
        return product_id

    async def update_products(self, products_data: List[Dict[str, Any]]) -> List[str]:
        """
        Update multiple existing products in storage in a batch operation.
        
        Args:
            products_data: List of dictionaries containing product data. Each must include 'id' field.
        
        Returns:
            List[str]: The IDs of the updated products, in the same order as the input.
        
        Raises:
            ProductNotFoundError: If any of the products are not found.
            ValueError: If any product_data doesn't contain an 'id' field.
            StorageConnectionError: If there's an error connecting to the storage.
        """
        if not products_data:
            return []
            
        # Verify all products have IDs and collect IDs to update
        product_ids = []
        for i, product_data in enumerate(products_data):
            if "id" not in product_data:
                raise ValueError(f"Product data at index {i} must include 'id' field")
            product_ids.append(str(product_data["id"]))
            
        # Check which products exist
        index = await self._load_index()
        missing_ids = [pid for pid in product_ids if pid not in index]
        
        if missing_ids:
            raise ProductNotFoundError(f"Products with IDs '{', '.join(missing_ids)}' not found")
            
        # Get all existing products to merge with updates
        existing_products = await self.get_products(product_ids)
        
        # Prepare updates
        updates = []
        now = datetime.now().isoformat()
        
        for i, (product_id, product_data, existing_product) in enumerate(
            zip(product_ids, products_data, existing_products)
        ):
            # Update the product data
            updated_product = {**existing_product, **product_data}
            
            # Update metadata
            updated_product["metadata"] = updated_product.get("metadata", {})
            updated_product["metadata"]["updated_at"] = now
            
            updates.append(updated_product)
            
            # Update the index
            index[product_id] = {
                "id": product_id,
                "metadata": updated_product["metadata"],
            }
            
            # Add key fields to the index for filtering
            for field in ["sku", "url", "store_name", "title"]:
                if field in updated_product:
                    index[product_id][field] = updated_product[field]
        
        # Save all updated products to files
        try:
            loop = asyncio.get_event_loop()
            tasks = []
            
            for product_id, updated_product in zip(product_ids, updates):
                file_path = self._get_file_path(product_id)
                tasks.append(loop.run_in_executor(
                    None,
                    lambda p=updated_product, f=file_path: json.dump(p, open(f, "w"))
                ))
                
            await asyncio.gather(*tasks)
        except (OSError, PermissionError) as e:
            raise StorageConnectionError(f"Failed to update products: {e}")
        
        # Update the index with all updated products
        await self._save_index(index)
        
        return product_ids

    async def delete_product(self, product_id: str) -> bool:
        """
        Delete a product from storage by ID.
        
        Args:
            product_id: The ID of the product to delete.
        
        Returns:
            bool: True if the product was deleted, False otherwise.
        
        Raises:
            ProductNotFoundError: If the product is not found.
            StorageConnectionError: If there's an error connecting to the storage.
        """
        index = await self._load_index()
        
        if product_id not in index:
            raise ProductNotFoundError(f"Product with ID '{product_id}' not found")
            
        # Remove the product file
        file_path = self._get_file_path(product_id)
        try:
            if os.path.exists(file_path):
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, os.remove, file_path)
        except (OSError, PermissionError) as e:
            raise StorageConnectionError(f"Failed to delete product: {e}")
        
        # Update the index
        del index[product_id]
        await self._save_index(index)
        
        return True

    async def delete_products(self, product_ids: List[str]) -> int:
        """
        Delete multiple products from storage by their IDs in a batch operation.
        
        Args:
            product_ids: List of product IDs to delete.
        
        Returns:
            int: The number of products that were deleted.
        
        Raises:
            ProductNotFoundError: If any of the products are not found.
            StorageConnectionError: If there's an error connecting to the storage.
        """
        if not product_ids:
            return 0
            
        index = await self._load_index()
        
        # Check which products exist
        missing_ids = [pid for pid in product_ids if pid not in index]
        
        if missing_ids:
            raise ProductNotFoundError(f"Products with IDs '{', '.join(missing_ids)}' not found")
            
        # Remove all product files in parallel
        try:
            loop = asyncio.get_event_loop()
            tasks = []
            
            for product_id in product_ids:
                file_path = self._get_file_path(product_id)
                if os.path.exists(file_path):
                    tasks.append(loop.run_in_executor(
                        None,
                        os.remove,
                        file_path
                    ))
                    
            await asyncio.gather(*tasks)
        except (OSError, PermissionError) as e:
            raise StorageConnectionError(f"Failed to delete products: {e}")
        
        # Update the index
        for product_id in product_ids:
            del index[product_id]
            
        await self._save_index(index)
        
        return len(product_ids)

    async def list_products(
        self,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> Dict[str, Any]:
        """
        List products with optional filtering, pagination, and sorting.
        
        Args:
            filters: Dictionary of field-value pairs to filter products by.
            page: Page number, starting from 1.
            page_size: Number of products per page.
            sort_by: Field to sort products by.
            sort_order: Sort order, either "asc" or "desc".
        
        Returns:
            Dict[str, Any]: Dictionary containing:
                - 'products': List of product data.
                - 'total': Total number of products matching the filters.
                - 'page': Current page number.
                - 'page_size': Number of products per page.
                - 'total_pages': Total number of pages.
        
        Raises:
            StorageConnectionError: If there's an error connecting to the storage.
        """
        # Load the index
        index = await self._load_index()
        
        # Filter the products
        filtered_product_ids = []
        for product_id, product_metadata in index.items():
            if filters and not self._matches_filters(product_metadata, filters):
                continue
            filtered_product_ids.append(product_id)
        
        # Sort the products
        if sort_by:
            def sort_key(product_id):
                if sort_by == "id":
                    return product_id
                elif sort_by.startswith("metadata."):
                    meta_field = sort_by.split(".", 1)[1]
                    metadata = index.get(product_id, {}).get("metadata", {})
                    return metadata.get(meta_field, "")
                else:
                    return index.get(product_id, {}).get(sort_by, "")
                
            filtered_product_ids = sorted(
                filtered_product_ids,
                key=sort_key,
                reverse=(sort_order.lower() == "desc")
            )
        
        # Paginate the products
        total = len(filtered_product_ids)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total)
        
        paginated_product_ids = filtered_product_ids[start_idx:end_idx]
        
        # Get the product data for the paginated IDs
        products = []
        if paginated_product_ids:
            try:
                products = await self.get_products(paginated_product_ids)
            except ProductNotFoundError:
                # This should not happen because we've already checked that the products exist
                # But just in case, we'll handle it gracefully
                products = []
        
        return {
            "products": products,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    def _matches_filters(self, product_metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """
        Check if a product's metadata matches the given filters.
        
        Args:
            product_metadata: Dictionary containing product metadata.
            filters: Dictionary of field-value pairs to filter products by.
        
        Returns:
            bool: True if the product matches the filters, False otherwise.
        """
        for field, value in filters.items():
            if field.startswith("metadata."):
                # Filter by metadata field
                meta_field = field.split(".", 1)[1]
                metadata = product_metadata.get("metadata", {})
                if meta_field not in metadata or metadata[meta_field] != value:
                    return False
            elif field not in product_metadata or product_metadata[field] != value:
                return False
                
        return True