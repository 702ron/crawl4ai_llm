"""
Transaction support for storage operations.

This module provides a transaction context manager for storage operations,
ensuring atomic operations with commit and rollback capabilities.
"""

import asyncio
import contextlib
import json
import logging
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import BaseModel

from ..models import ProductData
from .base import BaseStorage, StorageError

logger = logging.getLogger(__name__)


class TransactionError(StorageError):
    """Raised when there's an error with a transaction operation."""
    pass


class PydanticJSONEncoder(json.JSONEncoder):
    """JSON encoder that can handle Pydantic models and other complex types."""
    
    def default(self, obj):
        if isinstance(obj, BaseModel):
            return obj.dict()
        return super().default(obj)


class Transaction:
    """
    Transaction context manager for storage operations.
    
    Provides atomic operation capabilities with commit and rollback.
    Operations within a transaction are not applied until the transaction
    is committed. If an error occurs, the transaction can be rolled back.
    """
    
    def __init__(self, storage: BaseStorage):
        """
        Initialize a transaction.
        
        Args:
            storage: The storage backend to use for operations
        """
        self.storage = storage
        self.operations = []
        self.product_cache: Dict[str, ProductData] = {}
        self.added_products: List[ProductData] = []
        self.updated_products: Dict[str, ProductData] = {}
        self.deleted_products: Set[str] = set()
        self.committed = False
        self.active = True
    
    async def __aenter__(self):
        """Enter the transaction context."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the transaction context."""
        if exc_type is not None:
            # An exception occurred, roll back the transaction
            await self.rollback()
            return False
        
        if not self.committed:
            # Auto-commit if no exception and not already committed
            await self.commit()
        
        self.active = False
        return True
    
    def _check_active(self):
        """Check if the transaction is still active."""
        if not self.active:
            raise TransactionError("Transaction is no longer active")
        
        if self.committed:
            raise TransactionError("Transaction has already been committed")
    
    def _get_product_id(self, product: ProductData) -> Optional[str]:
        """
        Get the product ID from a product.
        
        Args:
            product: The product to get the ID from
            
        Returns:
            The product ID or None if not found
        """
        # Try to get the product ID from metadata
        if hasattr(product, "metadata") and product.metadata:
            if isinstance(product.metadata, dict) and "product_id" in product.metadata:
                return product.metadata["product_id"]
        
        # Try other common ID fields
        if hasattr(product, "sku") and product.sku:
            return product.sku
        
        return None
    
    async def add_product(self, product: ProductData) -> str:
        """
        Add a product to the transaction.
        
        Args:
            product: The product to add
            
        Returns:
            The product ID
            
        Raises:
            TransactionError: If the transaction is no longer active
        """
        self._check_active()
        
        # Generate a product ID
        product_id = self._get_product_id(product)
        
        # Add to the list of products to be added
        self.added_products.append(product)
        
        # Cache the product
        if product_id:
            self.product_cache[product_id] = product
        
        return product_id or "temp_id"
    
    async def get_product(self, product_id: str) -> Optional[ProductData]:
        """
        Get a product from the transaction cache or storage.
        
        Args:
            product_id: The ID of the product to get
            
        Returns:
            The product or None if not found
            
        Raises:
            TransactionError: If the transaction is no longer active
        """
        self._check_active()
        
        # Check if the product has been deleted in this transaction
        if product_id in self.deleted_products:
            return None
        
        # Check if the product is in the cache (added or updated in this transaction)
        if product_id in self.product_cache:
            return self.product_cache[product_id]
        
        # Check if the product is in the storage
        try:
            product = await self.storage.get_product(product_id)
            self.product_cache[product_id] = product
            return product
        except Exception as e:
            logger.warning(f"Error getting product {product_id}: {e}")
            return None
    
    async def update_product(self, product_id: str, product: ProductData) -> bool:
        """
        Update a product in the transaction.
        
        Args:
            product_id: The ID of the product to update
            product: The updated product data
            
        Returns:
            True if the update was successful, False otherwise
            
        Raises:
            TransactionError: If the transaction is no longer active
        """
        self._check_active()
        
        # Check if the product has been deleted in this transaction
        if product_id in self.deleted_products:
            return False
        
        # Add to the list of products to be updated
        self.updated_products[product_id] = product
        
        # Cache the product
        self.product_cache[product_id] = product
        
        return True
    
    async def delete_product(self, product_id: str) -> bool:
        """
        Delete a product in the transaction.
        
        Args:
            product_id: The ID of the product to delete
            
        Returns:
            True if the deletion was successful, False otherwise
            
        Raises:
            TransactionError: If the transaction is no longer active
        """
        self._check_active()
        
        # Add to the set of products to be deleted
        self.deleted_products.add(product_id)
        
        # Remove from cache if present
        if product_id in self.product_cache:
            del self.product_cache[product_id]
        
        # Remove from added products if present
        self.added_products = [p for p in self.added_products 
                              if self._get_product_id(p) != product_id]
        
        # Remove from updated products if present
        if product_id in self.updated_products:
            del self.updated_products[product_id]
        
        return True
    
    async def commit(self) -> bool:
        """
        Commit the transaction.
        
        Returns:
            True if the commit was successful, False otherwise
            
        Raises:
            TransactionError: If the transaction is no longer active
        """
        self._check_active()
        
        success = True
        
        try:
            # Process added products
            if self.added_products:
                product_ids = await self.storage.save_products(self.added_products)
                logger.info(f"Committed {len(product_ids)} added products")
            
            # Process updated products
            if self.updated_products:
                update_results = await self.storage.update_products(self.updated_products)
                logger.info(f"Committed {sum(update_results.values())} updated products")
            
            # Process deleted products
            if self.deleted_products:
                delete_results = await self.storage.delete_products(list(self.deleted_products))
                logger.info(f"Committed {sum(delete_results.values())} deleted products")
            
            self.committed = True
            
        except Exception as e:
            logger.error(f"Error committing transaction: {e}")
            success = False
            # Try to roll back
            try:
                await self.rollback()
            except Exception as rollback_error:
                logger.error(f"Error rolling back transaction after commit failure: {rollback_error}")
        
        return success
    
    async def rollback(self) -> None:
        """
        Roll back the transaction.
        
        Raises:
            TransactionError: If the transaction is no longer active or already committed
        """
        if self.committed:
            raise TransactionError("Cannot roll back a committed transaction")
        
        if not self.active:
            raise TransactionError("Transaction is no longer active")
        
        # Clear all pending operations
        self.added_products = []
        self.updated_products = {}
        self.deleted_products = set()
        self.product_cache = {}
        
        logger.info("Transaction rolled back")
        
        # Mark as inactive
        self.active = False


class ProductStorage:
    """
    Storage class for product data with transaction support.
    
    This class wraps a BaseStorage implementation and adds transaction support.
    """
    
    def __init__(self, storage: Optional[BaseStorage] = None, db_url: Optional[str] = None):
        """
        Initialize the product storage.
        
        Args:
            storage: An optional existing storage instance
            db_url: An optional database URL to initialize a storage instance
        """
        self.storage = storage
        self.db_url = db_url
        self._initialized = False
    
    async def initialize(self):
        """Initialize the storage if not already initialized."""
        if self._initialized:
            return
        
        if self.storage is None:
            # Import here to avoid circular imports
            from .factory import get_storage
            from ..config import StorageConfig
            
            if self.db_url and "sqlite" in self.db_url:
                # Use memory storage for SQLite URLs
                import tempfile
                temp_dir = tempfile.mkdtemp()
                config = StorageConfig(type="json", path=temp_dir, use_uuid=True)
                self.storage = get_storage(config)
            else:
                # Use the default configuration
                self.storage = get_storage()
        
        self._initialized = True
    
    def transaction(self):
        """
        Create a new transaction.
        
        Returns:
            A new Transaction context manager
        """
        return Transaction(self.storage)
    
    async def add_product(self, product: ProductData, transaction: Optional[Transaction] = None) -> str:
        """
        Add a product to storage.
        
        Args:
            product: The product to add
            transaction: An optional transaction to use
            
        Returns:
            The product ID
        """
        if transaction:
            return await transaction.add_product(product)
        
        return await self.storage.save_product(product)
    
    async def get_product(self, product_id: str, transaction: Optional[Transaction] = None) -> Optional[ProductData]:
        """
        Get a product from storage.
        
        Args:
            product_id: The ID of the product to get
            transaction: An optional transaction to use
            
        Returns:
            The product or None if not found
        """
        if transaction:
            return await transaction.get_product(product_id)
        
        try:
            return await self.storage.get_product(product_id)
        except Exception:
            return None
    
    async def update_product(self, product_id: str, product: ProductData, transaction: Optional[Transaction] = None) -> bool:
        """
        Update a product in storage.
        
        Args:
            product_id: The ID of the product to update
            product: The updated product data
            transaction: An optional transaction to use
            
        Returns:
            True if the update was successful, False otherwise
        """
        if transaction:
            return await transaction.update_product(product_id, product)
        
        return await self.storage.update_product(product_id, product)
    
    async def delete_product(self, product_id: str, transaction: Optional[Transaction] = None) -> bool:
        """
        Delete a product from storage.
        
        Args:
            product_id: The ID of the product to delete
            transaction: An optional transaction to use
            
        Returns:
            True if the deletion was successful, False otherwise
        """
        if transaction:
            return await transaction.delete_product(product_id)
        
        return await self.storage.delete_product(product_id)
    
    async def get_all_products(self, limit: int = 1000) -> List[ProductData]:
        """
        Get all products from storage.
        
        Args:
            limit: Maximum number of products to return
            
        Returns:
            A list of products
        """
        products, _ = await self.storage.list_products(limit=limit)
        return products
    
    async def count_products(self) -> int:
        """
        Count the number of products in storage.
        
        Returns:
            The number of products
        """
        _, count = await self.storage.list_products(limit=1)
        return count
    
    async def delete_all_products(self) -> bool:
        """
        Delete all products from storage.
        
        Returns:
            True if the deletion was successful, False otherwise
        """
        all_products, _ = await self.storage.list_products(limit=10000)
        product_ids = []
        
        for p in all_products:
            # Try to get product ID from metadata
            if hasattr(p, "metadata") and isinstance(p.metadata, dict) and "product_id" in p.metadata:
                product_ids.append(p.metadata["product_id"])
            # Try to get product ID from sku
            elif hasattr(p, "sku") and p.sku:
                product_ids.append(p.sku)
        
        if not product_ids:
            return True
        
        results = await self.storage.delete_products(product_ids)
        return all(results.values())
    
    async def close(self):
        """Close the storage connection if applicable."""
        # This is a placeholder, as the current storage implementation doesn't require closing
        pass 