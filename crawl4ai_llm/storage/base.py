"""
Base storage interface for product data persistence.

This module defines abstract base classes for various storage implementations.
"""

import abc
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

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

    @abc.abstractmethod
    async def save_products(self, product_data_list: List[ProductData]) -> List[str]:
        """
        Save multiple products to storage in a batch operation.

        Args:
            product_data_list: List of ProductData objects to save

        Returns:
            List of string identifiers for the saved products

        Raises:
            StorageConnectionError: If there's an issue connecting to storage
        """
        pass

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

    @abc.abstractmethod
    async def get_products(self, product_ids: List[str]) -> Dict[str, ProductData]:
        """
        Retrieve multiple products by their IDs in a batch operation.

        Args:
            product_ids: List of product IDs to retrieve

        Returns:
            Dictionary mapping product IDs to their ProductData objects

        Raises:
            StorageConnectionError: If there's an issue connecting to storage
        """
        pass

    @abc.abstractmethod
    async def update_product(self, product_id: str, product_data: ProductData) -> bool:
        """
        Update existing product data.

        Args:
            product_id: Unique identifier for the product
            product_data: ProductData object containing updated product data

        Returns:
            True if update was successful, False otherwise

        Raises:
            ProductNotFoundError: If the product is not found
            StorageConnectionError: If there's an issue connecting to storage
        """
        pass

    @abc.abstractmethod
    async def update_products(self, updates: Dict[str, ProductData]) -> Dict[str, bool]:
        """
        Update multiple products in a batch operation.

        Args:
            updates: Dictionary mapping product IDs to their updated ProductData objects

        Returns:
            Dictionary mapping product IDs to update success status (True/False)

        Raises:
            StorageConnectionError: If there's an issue connecting to storage
        """
        pass

    @abc.abstractmethod
    async def delete_product(self, product_id: str) -> bool:
        """
        Delete a product from storage.

        Args:
            product_id: Unique identifier for the product

        Returns:
            True if deletion was successful, False otherwise

        Raises:
            ProductNotFoundError: If the product is not found
            StorageConnectionError: If there's an issue connecting to storage
        """
        pass

    @abc.abstractmethod
    async def delete_products(self, product_ids: List[str]) -> Dict[str, bool]:
        """
        Delete multiple products in a batch operation.

        Args:
            product_ids: List of product IDs to delete

        Returns:
            Dictionary mapping product IDs to deletion success status (True/False)

        Raises:
            StorageConnectionError: If there's an issue connecting to storage
        """
        pass

    @abc.abstractmethod
    async def list_products(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> Tuple[List[ProductData], int]:
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

    @abc.abstractmethod
    async def get_product_version(self, product_id: str, version: int) -> ProductData:
        """
        Get a specific version of a product.

        Args:
            product_id: The ID of the product
            version: The version number to retrieve

        Returns:
            ProductData object for the specified version

        Raises:
            ProductNotFoundError: If the product or version is not found
            StorageConnectionError: If there's an issue connecting to storage
        """
        pass

    @abc.abstractmethod
    async def list_product_versions(self, product_id: str) -> List[Dict[str, Any]]:
        """
        List all available versions of a product.

        Args:
            product_id: The ID of the product

        Returns:
            List of dictionaries containing version metadata

        Raises:
            ProductNotFoundError: If the product is not found
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
