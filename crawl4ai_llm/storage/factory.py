"""
Factory for creating storage instances.

This module provides a factory function for creating storage instances
based on configuration.
"""

import logging
from typing import Dict, Type, Optional

from ..config import StorageConfig
from .base import BaseStorage
from .json_storage import JSONStorage

logger = logging.getLogger(__name__)

# Registry of available storage implementations
STORAGE_REGISTRY: Dict[str, Type[BaseStorage]] = {
    "json": JSONStorage,
}

# Singleton storage instance
_storage_instance: Optional[BaseStorage] = None


def get_storage(config: StorageConfig) -> BaseStorage:
    """
    Get or create a storage instance based on configuration.
    
    Args:
        config: Storage configuration
        
    Returns:
        Storage instance
        
    Raises:
        ValueError: If the storage type is unknown
    """
    global _storage_instance
    
    if _storage_instance is None:
        storage_class = STORAGE_REGISTRY.get(config.type.lower())
        
        if storage_class is None:
            raise ValueError(f"Unknown storage type: {config.type}")
        
        logger.info(f"Initializing {config.type} storage at {config.path}")
        _storage_instance = storage_class(config)
    
    return _storage_instance