"""
Base storage interface for product data persistence.

This module defines abstract base classes for various storage implementations.
"""

import abc
from typing import Dict, List, Any, Optional, Union, Tuple, Sequence
from datetime import datetime
import logging

from ..models import ProductData

logger = logging.getLogger(__name__)


class BaseStorage(abc.ABC):
    """
    Abstract base class for product data storage implementations.
    
    All storage implementations should inherit from this class
    and implement its abstract methods.
    """
    
    @abc.abstractmethod
    async def save_product(self, product_data: ProductData) -> str:
        """
        Save product data to storage.
        
        Args:
            product_data: ProductData object containing product data
            
        Returns:
            String identifier for the saved product
            
        Raises:
            DuplicateProductError: If the product already exists
            StorageConnectionError: If there's an issue connecting to storage
        """
        pass
    
    async def save_products(self, products: Sequence[ProductData]) -> List[str]:
        """
        Save multiple products to storage.
        
        This is a convenience method that calls save_product for each product.
        Implementations should override this method for better performance.
        
        Args:
            products: Sequence of ProductData objects
            
        Returns:
            List of product IDs for successfully saved products
            
        Raises:
            StorageConnectionError: If there's an issue connecting to storage
        """
        product_ids = []
        for product in products:
            try:
                product_id = await self.save_product(product)
                product_ids.append(product_id)
            except Exception as e:
                logger.error(f"Error saving product: {str(e)}")
        
        return product_ids
    
    @abc.abstractmethod
    async def get_product(self, product_id: str) -> ProductData:
        """
        Retrieve product data by ID.
        
        Args:
            product_id: Unique identifier for the product
            
        Returns:
            ProductData object containing product data
            
        Raises:
            ProductNotFoundError: If the product is not found
            StorageConnectionError: If there's an issue connecting to storage
        """
        pass
    
    async def get_products(self, product_ids: Sequence[str]) -> List[ProductData]:
        """
        Retrieve multiple products by ID.
        
        This is a convenience method that calls get_product for each ID.
        Implementations should override this method for better performance.
        
        Args:
            product_ids: Sequence of product IDs
            
        Returns:
            List of ProductData objects for found products
            
        Raises:
            StorageConnectionError: If there's an issue connecting to storage
        """
        products = []
        for product_id in product_ids:
            try:
                product = await self.get_product(product_id)
                products.append(product)
            except ProductNotFoundError:
                logger.warning(f"Product not found: {product_id}")
            except Exception as e:
                logger.error(f"Error retrieving product: {str(e)}")
        
        return products
    
    @abc.abstractmethod
    async def update_product(self, product_id: str, product_data: ProductData) -> bool:
        """
        Update existing product data.
        
        Args:
            product_id: Unique identifier for the product
            product_data: ProductData object containing updated product data
            
        Returns:
            Boolean indicating success of the update operation
            
        Raises:
            ProductNotFoundError: If the product is not found
            StorageConnectionError: If there's an issue connecting to storage
        """
        pass
    
    async def update_products(self, products: Dict[str, ProductData]) -> Dict[str, bool]:
        """
        Update multiple products.
        
        This is a convenience method that calls update_product for each product.
        Implementations should override this method for better performance.
        
        Args:
            products: Dictionary mapping product IDs to updated ProductData objects
            
        Returns:
            Dictionary mapping product IDs to update success (True/False)
            
        Raises:
            StorageConnectionError: If there's an issue connecting to storage
        """
        results = {}
        for product_id, product_data in products.items():
            try:
                result = await self.update_product(product_id, product_data)
                results[product_id] = result
            except ProductNotFoundError:
                logger.warning(f"Product not found: {product_id}")
                results[product_id] = False
            except Exception as e:
                logger.error(f"Error updating product: {str(e)}")
                results[product_id] = False
        
        return results
    
    @abc.abstractmethod
    async def delete_product(self, product_id: str) -> bool:
        """
        Delete a product from storage.
        
        Args:
            product_id: Unique identifier for the product
            
        Returns:
            Boolean indicating success of the delete operation
            
        Raises:
            ProductNotFoundError: If the product is not found
            StorageConnectionError: If there's an issue connecting to storage
        """
        pass
    
    async def delete_products(self, product_ids: Sequence[str]) -> Dict[str, bool]:
        """
        Delete multiple products.
        
        This is a convenience method that calls delete_product for each ID.
        Implementations should override this method for better performance.
        
        Args:
            product_ids: Sequence of product IDs to delete
            
        Returns:
            Dictionary mapping product IDs to deletion success (True/False)
            
        Raises:
            StorageConnectionError: If there's an issue connecting to storage
        """
        results = {}
        for product_id in product_ids:
            try:
                result = await self.delete_product(product_id)
                results[product_id] = result
            except ProductNotFoundError:
                logger.warning(f"Product not found: {product_id}")
                results[product_id] = False
            except Exception as e:
                logger.error(f"Error deleting product: {str(e)}")
                results[product_id] = False
        
        return results
    
    @abc.abstractmethod
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
            Tuple[List[ProductData], int]: List of products and total count
            
        Raises:
            StorageConnectionError: If there's an issue connecting to storage
        """
        pass
    

class StorageError(Exception):
    """Base exception for storage-related errors."""
    pass


class ProductNotFoundError(StorageError):
    """Raised when trying to access a product that doesn't exist."""
    pass


class DuplicateProductError(StorageError):
    """Raised when trying to create a product that already exists."""
    pass


class StorageConnectionError(StorageError):
    """Raised when there's an error connecting to the storage backend."""
    pass