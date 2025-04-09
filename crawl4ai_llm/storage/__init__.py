"""
Storage layer for product data.
"""

from .json_storage import JSONStorage
from .factory import get_storage
from .base import (
    BaseStorage, 
    StorageError, 
    ProductNotFoundError, 
    DuplicateProductError, 
    StorageConnectionError
)

__all__ = [
    "JSONStorage",
    "get_storage",
    "BaseStorage",
    "StorageError",
    "ProductNotFoundError",
    "DuplicateProductError",
    "StorageConnectionError"
] 