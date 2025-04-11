"""
Factory for creating storage instances.

This module provides a factory function to instantiate storage backends based on configuration.
All storage implementations support both individual and batch operations for products.
"""

import logging
from typing import Any, Dict, Optional, Type

from ..config import StorageConfig
from .json_storage import JSONStorage

logger = logging.getLogger(__name__)

# Registry of available storage implementations
STORAGE_REGISTRY: Dict[str, Type[Any]] = {
    "json": JSONStorage,  # File-based JSON storage with batch operation support
}

# Singleton storage instance
_storage_instance = None


def get_storage(config: Optional[StorageConfig] = None):
    """
    Get or create a storage instance based on configuration.

    All storage implementations support the following operations:
    - Individual operations: save_product, get_product, update_product, delete_product
    - Batch operations: save_products, get_products, update_products, delete_products
    - Listing: list_products with filtering, pagination, and sorting

    Args:
        config: Storage configuration (optional)

    Returns:
        A storage instance implementing the BaseStorage interface

    Raises:
        ValueError: If storage type is unknown
    """
    global _storage_instance

    if _storage_instance is not None:
        return _storage_instance

    if config is None:
        from ..config import get_config

        config = get_config().storage

    storage_type = config.type.lower()

    if storage_type not in STORAGE_REGISTRY:
        raise ValueError(f"Unknown storage type: {storage_type}")

    storage_class = STORAGE_REGISTRY[storage_type]

    if storage_type == "json":
        _storage_instance = storage_class(
            storage_dir=config.path, 
            use_uuid=config.use_uuid,
            versioning_enabled=config.versioning_enabled
        )
    else:
        _storage_instance = storage_class(config.path)

    logger.info(f"Initialized {storage_type} storage at {config.path}")
    return _storage_instance
