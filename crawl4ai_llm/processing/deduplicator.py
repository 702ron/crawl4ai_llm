"""
Module for product deduplication functionality.

This module provides tools to detect and handle duplicate product entries
based on various criteria like ID matching or content similarity.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple
from difflib import SequenceMatcher
from enum import Enum
from datetime import datetime

from ..models import ProductData

logger = logging.getLogger(__name__)


class MergeStrategy(str, Enum):
    """Defines strategies for merging duplicate products."""
    
    LATEST = "latest"  # Keep the most recently extracted product
    MOST_COMPLETE = "most_complete"  # Keep the product with the most fields filled
    COMBINE = "combine"  # Combine data from both products


class DataProcessingError(Exception):
    """Base exception for data processing errors."""
    pass


class Deduplicator:
    """
    Class responsible for detecting and handling duplicate products.
    
    Provides methods to:
    - Generate product signatures 
    - Check for duplicates by ID or content similarity
    - Group duplicate products
    - Merge duplicate products using different strategies
    """
    
    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize the deduplicator.
        
        Args:
            similarity_threshold: Float between 0 and 1 that determines the
                minimum similarity score to consider products as duplicates.
                Higher values mean stricter matching. Default is 0.85.
        """
        self.similarity_threshold = similarity_threshold
        logger.debug(f"Initialized Deduplicator with similarity threshold: {similarity_threshold}")
    
    def product_signature(self, product: ProductData) -> Dict[str, str]:
        """
        Generate a signature dictionary for a product based on its key attributes.
        
        Args:
            product: The product data to generate a signature for.
            
        Returns:
            A dictionary containing product identifiers and key attributes.
        """
        signature = {}
        
        # Add product identifiers if available
        if product.sku:
            signature["sku"] = product.sku
        if product.upc:
            signature["upc"] = product.upc
        if product.ean:
            signature["ean"] = product.ean
        if product.isbn:
            signature["isbn"] = product.isbn
        if product.mpn:
            signature["mpn"] = product.mpn
        if product.gtin:
            signature["gtin"] = product.gtin
        
        # Add key attributes
        if product.brand:
            signature["brand"] = product.brand.lower().strip()
        
        signature["title"] = product.title.lower().strip()
        
        return signature
    
    def is_duplicate_by_id(self, product1: ProductData, product2: ProductData) -> bool:
        """
        Check if two products are duplicates based on their identifiers.
        
        Args:
            product1: First product to compare
            product2: Second product to compare
            
        Returns:
            True if the products are duplicates, False otherwise
        """
        if product1 is product2:
            return True
            
        # Get signatures for both products
        sig1 = self.product_signature(product1)
        sig2 = self.product_signature(product2)
        
        # Check for matching identifiers
        for id_field in ["sku", "upc", "ean", "isbn", "mpn", "gtin"]:
            if id_field in sig1 and id_field in sig2:
                if sig1[id_field] and sig2[id_field] and sig1[id_field] == sig2[id_field]:
                    logger.debug(f"Duplicate detected by {id_field}: {sig1[id_field]}")
                    return True
                    
        return False
    
    def text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two text strings using sequence matching.
        
        Args:
            text1: First text string
            text2: Second text string
            
        Returns:
            Similarity score between 0 and 1
        """
        if not text1 or not text2:
            return 0.0
            
        text1 = text1.lower().strip()
        text2 = text2.lower().strip()
        
        return SequenceMatcher(None, text1, text2).ratio()
    
    def calculate_similarity(self, product1: ProductData, product2: ProductData) -> float:
        """
        Calculate overall similarity between two products.
        
        Args:
            product1: First product to compare
            product2: Second product to compare
            
        Returns:
            Similarity score between 0 and 1
        """
        # If they're already duplicates by ID, return 1.0
        if self.is_duplicate_by_id(product1, product2):
            return 1.0
        
        # Calculate weighted similarity scores
        title_similarity = self.text_similarity(product1.title, product2.title)
        
        # Compare brand if available
        brand_similarity = 0.0
        if product1.brand and product2.brand:
            brand_similarity = self.text_similarity(product1.brand, product2.brand)
        
        # Compare description if available
        desc_similarity = 0.0
        if product1.description and product2.description:
            desc_similarity = self.text_similarity(product1.description, product2.description)
        
        # Assign weights to different attributes
        weights = {
            "title": 0.5,
            "brand": 0.3,
            "description": 0.2
        }
        
        # Calculate weighted score
        similarity_score = (
            weights["title"] * title_similarity + 
            weights["brand"] * brand_similarity + 
            weights["description"] * desc_similarity
        )
        
        # Normalize if not all attributes are available
        available_weight = weights["title"]
        if product1.brand and product2.brand:
            available_weight += weights["brand"]
        if product1.description and product2.description:
            available_weight += weights["description"]
        
        normalized_score = similarity_score / available_weight if available_weight > 0 else 0
        
        logger.debug(f"Similarity score between products: {normalized_score:.2f}")
        return normalized_score
    
    def is_duplicate_by_similarity(self, product1: ProductData, product2: ProductData) -> bool:
        """
        Check if two products are duplicates based on content similarity.
        
        Args:
            product1: First product to compare
            product2: Second product to compare
            
        Returns:
            True if the products are similar enough to be considered duplicates
        """
        similarity = self.calculate_similarity(product1, product2)
        return similarity >= self.similarity_threshold
    
    def find_duplicates(self, products: List[ProductData]) -> List[Set[int]]:
        """
        Find groups of duplicate products within a list.
        
        Args:
            products: List of products to check for duplicates
            
        Returns:
            List of sets, where each set contains indices of duplicate products
        """
        if not products:
            return []
        
        n = len(products)
        # Track which products have been assigned to a group
        assigned = [False] * n
        duplicate_groups = []
        
        for i in range(n):
            if assigned[i]:
                continue
                
            # Start a new group with this product
            group = {i}
            assigned[i] = True
            
            # Check against all other unassigned products
            for j in range(i + 1, n):
                if assigned[j]:
                    continue
                    
                if (self.is_duplicate_by_id(products[i], products[j]) or 
                    self.is_duplicate_by_similarity(products[i], products[j])):
                    group.add(j)
                    assigned[j] = True
            
            # Only add groups with more than one product (duplicates)
            if len(group) > 1:
                duplicate_groups.append(group)
        
        return duplicate_groups
    
    def merge_products(
        self, 
        products: List[ProductData], 
        strategy: MergeStrategy = MergeStrategy.MOST_COMPLETE
    ) -> ProductData:
        """
        Merge multiple duplicate products into a single product.
        
        Args:
            products: List of duplicate products to merge
            strategy: Strategy to use for merging (latest, most_complete, or combine)
            
        Returns:
            A merged product
            
        Raises:
            DataProcessingError: If the product list is empty
        """
        if not products:
            raise DataProcessingError("Cannot merge empty product list")
            
        if len(products) == 1:
            return products[0]
            
        if strategy == MergeStrategy.LATEST:
            # Find the product with the most recent extraction timestamp
            latest_product = products[0]
            latest_time = None
            
            for product in products:
                if product.extracted_at:
                    try:
                        current_time = datetime.fromisoformat(product.extracted_at)
                        if latest_time is None or current_time > latest_time:
                            latest_time = current_time
                            latest_product = product
                    except (ValueError, TypeError):
                        # If timestamp is invalid, skip this product
                        continue
            
            return latest_product
            
        elif strategy == MergeStrategy.MOST_COMPLETE:
            # Find the product with the most non-empty fields
            def count_filled_fields(p: ProductData) -> int:
                # Convert to dict and count non-None values
                p_dict = p.dict()
                return sum(1 for v in p_dict.values() if v is not None)
            
            # Return the product with the most filled fields
            return max(products, key=count_filled_fields)
            
        elif strategy == MergeStrategy.COMBINE:
            # Create a new product combining all non-empty fields
            # Start with the most complete product as base
            base_product = self.merge_products(products, MergeStrategy.MOST_COMPLETE)
            base_dict = base_product.dict()
            
            for product in products:
                if product == base_product:
                    continue
                    
                product_dict = product.dict()
                
                # Fill in missing fields from other products
                for field, value in product_dict.items():
                    if base_dict[field] is None and value is not None:
                        base_dict[field] = value
            
            # Create a new product with the combined data
            return ProductData(**base_dict)
        
        else:
            raise DataProcessingError(f"Unknown merge strategy: {strategy}")


def get_duplicate_groups(
    products: List[ProductData], 
    similarity_threshold: float = 0.85
) -> List[List[ProductData]]:
    """
    Find groups of duplicate products in a list.
    
    Args:
        products: List of products to check for duplicates
        similarity_threshold: Threshold for similarity-based duplicate detection
        
    Returns:
        List of lists, where each inner list contains duplicate products
    """
    deduplicator = Deduplicator(similarity_threshold=similarity_threshold)
    duplicate_indices = deduplicator.find_duplicates(products)
    
    # Convert sets of indices to lists of products
    duplicate_groups = []
    for index_group in duplicate_indices:
        group = [products[i] for i in index_group]
        duplicate_groups.append(group)
    
    return duplicate_groups 