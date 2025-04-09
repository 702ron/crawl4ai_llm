"""
Base interface and exceptions for storage implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class StorageError(Exception):
    """Base exception for all storage-related errors."""
    pass


class StorageConnectionError(StorageError):
    """Raised when there's an error connecting to the storage system."""
    pass


class ProductNotFoundError(StorageError):
    """Raised when a product is not found in storage."""
    pass


class DuplicateProductError(StorageError):
    """Raised when trying to save a product with an ID that already exists."""
    pass


class BaseStorage(ABC):
    """Base interface for storage implementations."""

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass