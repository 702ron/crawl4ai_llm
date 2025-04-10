"""
Storage layer for crawl4ai_llm.

This package provides storage capabilities for product data.
"""

from .base import (
    BaseStorage, 
    StorageError,
    ProductNotFoundError,
    DuplicateProductError
)
from .factory import get_storage
from .json_storage import JSONStorage
from .transaction import Transaction, TransactionError, ProductStorage, PydanticJSONEncoder

__all__ = [
    'BaseStorage',
    'StorageError',
    'ProductNotFoundError',
    'DuplicateProductError',
    'get_storage',
    'JSONStorage',
    'Transaction',
    'TransactionError',
    'ProductStorage',
    'PydanticJSONEncoder',
]
