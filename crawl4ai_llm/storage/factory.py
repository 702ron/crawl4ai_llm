"""
Factory for creating storage instances.

This module provides a factory function for creating storage instances based on
the storage configuration. Supported storage types include JSON file storage.
"""

import logging
from typing import Optional, Dict, Any

from ..config import StorageConfig
from .base import BaseStorage
from .json_storage import JSONStorage

logger = logging.getLogger(__name__)

# Registry of available storage implementations
STORAGE_REGISTRY = {
    "json": JSONStorage,
}

# Singleton storage instance
_storage_instance: Optional[BaseStorage] = None


async def get_storage(config: StorageConfig) -> BaseStorage:
    """
    Get or create a storage instance based on the configuration.
    
    Args:
        config: Storage configuration.
        
    Returns:
        BaseStorage: A storage instance.
        
    Raises:
        ValueError: If the storage type is unknown.
    """
    global _storage_instance
    
    # Return the singleton instance if it already exists
    if _storage_instance is not None:
        return _storage_instance
    
    # Get the storage implementation class
    storage_type = config.type.lower()
    if storage_type not in STORAGE_REGISTRY:
        raise ValueError(f"Unknown storage type: {storage_type}")
    
    storage_class = STORAGE_REGISTRY[storage_type]
    
    # Extract the configuration parameters
    params: Dict[str, Any] = {}
    if storage_type == "json":
        params["directory"] = config.json_directory
        if config.lock_timeout:
            params["lock_timeout"] = config.lock_timeout
    
    # Create the storage instance
    logger.info(f"Initializing {storage_type} storage")
    _storage_instance = storage_class(**params)
    
    return _storage_instance