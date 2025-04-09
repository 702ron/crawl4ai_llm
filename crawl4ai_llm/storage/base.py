"""
Base Storage Interface.

This module defines the base interface for storage implementations.
"""

import abc
from typing import Dict, List, Any, Optional, Union


class StorageError(Exception):
    """Base exception for all storage-related errors."""
    pass


class StorageConnectionError(StorageError):
    """Exception raised when a connection to the storage cannot be established."""
    pass


class ProductNotFoundError(StorageError):
    """Exception raised when a product is not found in the storage."""
    pass


class DuplicateProductError(StorageError):
    """Exception raised when attempting to save a product that already exists."""
    pass


class BaseStorage(abc.ABC):
    """Base storage interface for saving and retrieving product data."""
    
    @abc.abstractmethod
    async def save_product(self, product_data: Dict[str, Any]) -> str:
        """
        Save a product to the storage.
        
        Args:
            product_data: A dictionary containing product data.
            
        Returns:
            str: The ID of the saved product.
            
        Raises:
            DuplicateProductError: If a product with the same ID already exists.
            StorageConnectionError: If a connection to the storage cannot be established.
        """
        pass
    
    @abc.abstractmethod
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
        pass
    
    @abc.abstractmethod
    async def get_product(self, product_id: str) -> Dict[str, Any]:
        """
        Get a product from the storage by its ID.
        
        Args:
            product_id: The ID of the product to retrieve.
            
        Returns:
            Dict[str, Any]: The product data.
            
        Raises:
            ProductNotFoundError: If the product is not found.
            StorageConnectionError: If a connection to the storage cannot be established.
        """
        pass
    
    @abc.abstractmethod
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
        pass
    
    @abc.abstractmethod
    async def update_product(self, product_id: str, product_data: Dict[str, Any]) -> str:
        """
        Update a product in the storage.
        
        Args:
            product_id: The ID of the product to update.
            product_data: A dictionary containing updated product data.
            
        Returns:
            str: The ID of the updated product.
            
        Raises:
            ProductNotFoundError: If the product is not found.
            StorageConnectionError: If a connection to the storage cannot be established.
        """
        pass
    
    @abc.abstractmethod
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
        pass
    
    @abc.abstractmethod
    async def delete_product(self, product_id: str) -> bool:
        """
        Delete a product from the storage.
        
        Args:
            product_id: The ID of the product to delete.
            
        Returns:
            bool: True if the product was deleted, False otherwise.
            
        Raises:
            ProductNotFoundError: If the product is not found.
            StorageConnectionError: If a connection to the storage cannot be established.
        """
        pass
    
    @abc.abstractmethod
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
        pass
    
    @abc.abstractmethod
    async def list_products(
        self,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 50,
        sort_by: Optional[str] = None,
        sort_order: str = "asc"
    ) -> Dict[str, Any]:
        """
        List products in the storage with optional filtering, pagination and sorting.
        
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
            StorageConnectionError: If a connection to the storage cannot be established.
        """
        pass