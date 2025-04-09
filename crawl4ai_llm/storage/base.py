"""
Base interface and exceptions for storage implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, Optional, Union

from ..models import ProductData


class StorageError(Exception):
    """Base class for storage-related exceptions."""
    pass


class ProductNotFoundError(StorageError):
    """Raised when a product is not found in storage."""
    pass


class DuplicateProductError(StorageError):
    """Raised when attempting to save a product that already exists."""
    pass


class StorageConnectionError(StorageError):
    """Raised when there's an error connecting to the storage system."""
    pass


class BaseStorage(ABC):
    """
    Base storage interface for product data.
    
    All storage implementations must implement these methods.
    """
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def list_products(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None
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
        pass