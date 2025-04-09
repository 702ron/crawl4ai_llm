"""
Storage module for product data persistence.
"""

from .base import (
    BaseStorage,
    StorageError,
    ProductNotFoundError,
    DuplicateProductError,
    StorageConnectionError
)
from .json_storage import JSONStorage
from .factory import get_storage

__all__ = [
    'BaseStorage',
    'JSONStorage',
    'get_storage',
    'StorageError',
    'ProductNotFoundError',
    'DuplicateProductError',
    'StorageConnectionError'
]