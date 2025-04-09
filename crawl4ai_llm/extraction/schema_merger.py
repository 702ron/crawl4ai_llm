"""
Schema merger utility for product extraction.

This module provides functionality to merge multiple schemas
for improved extraction accuracy.
"""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from .schema_validator import SchemaValidator, SchemaField

logger = logging.getLogger(__name__)


class SchemaMerger:
    """
    Merges multiple extraction schemas into an optimized schema.
    
    This class analyzes and combines multiple extraction schemas to create
    a more robust and accurate schema for product extraction.
    """
    
    def __init__(self, quality_threshold: float = 0.6):
        """
        Initialize a schema merger with a quality threshold.
        
        Args:
            quality_threshold: Minimum quality score for inclusion in the merged schema.
        """
        self.quality_threshold = quality_threshold
        self.validator = SchemaValidator()
        
    def merge(self, schemas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge multiple schemas into an optimized schema.
        
        Args:
            schemas: List of schemas to merge.
            
        Returns:
            A merged schema optimized for extraction accuracy.
        """
        if not schemas:
            return {"fields": []}
            
        if len(schemas) == 1:
            return schemas[0]
        
        # Validate and score each schema
        scored_schemas = []
        for schema in schemas:
            is_valid, _ = self.validator.validate(schema)
            if not is_valid:
                schema = self.validator.correct_schema(schema)
                
            quality_score = self.validator._calculate_quality_score(schema)
            scored_schemas.append((schema, quality_score))
        
        # Sort schemas by quality score (highest first)
        scored_schemas.sort(key=lambda x: x[1], reverse=True)
        
        # Skip schemas below quality threshold
        valid_schemas = [schema for schema, score in scored_schemas if score >= self.quality_threshold]
        
        if not valid_schemas:
            # If no schema passes threshold, use the highest scored one
            return scored_schemas[0][0]
        
        # Start with the highest quality schema
        merged_schema = {"fields": []}
        field_map = {}  # Maps field names to their indices in the merged_schema fields list
        
        # Merge fields from each schema
        for schema in valid_schemas:
            for field_data in schema.get("fields", []):
                # Convert to SchemaField for consistent handling
                try:
                    field = SchemaField.from_dict(field_data)
                except Exception as e:
                    logger.warning(f"Skipping invalid field: {e}")
                    continue
                
                # Check if we already have this field
                if field.name in field_map:
                    # Field exists, consider updating or enhancing it
                    existing_idx = field_map[field.name]
                    existing_field = SchemaField.from_dict(merged_schema["fields"][existing_idx])
                    
                    # Check if new field has a better selector
                    if self._compare_selectors(field.selector, existing_field.selector):
                        merged_schema["fields"][existing_idx]["selector"] = field.selector
                    
                    # Keep the field required if either is required
                    if field.required:
                        merged_schema["fields"][existing_idx]["required"] = True
                    
                    # Use appropriate attribute
                    if self._is_better_attribute(field.attribute, existing_field.attribute):
                        merged_schema["fields"][existing_idx]["attribute"] = field.attribute
                        
                    # Merge array property logically
                    merged_schema["fields"][existing_idx]["array"] = (
                        existing_field.array or field.array
                    )
                    
                    # Combine descriptions if available
                    if field.description and existing_field.description:
                        if len(field.description) > len(existing_field.description):
                            merged_schema["fields"][existing_idx]["description"] = field.description
                    elif field.description:
                        merged_schema["fields"][existing_idx]["description"] = field.description
                        
                else:
                    # New field, add it to merged schema
                    field_dict = field.to_dict()
                    merged_schema["fields"].append(field_dict)
                    field_map[field.name] = len(merged_schema["fields"]) - 1
        
        # Ensure the merged schema passes validation
        is_valid, _ = self.validator.validate(merged_schema)
        if not is_valid:
            return self.validator.correct_schema(merged_schema)
            
        return merged_schema
    
    def _compare_selectors(self, new_selector: str, existing_selector: str) -> bool:
        """
        Compare two selectors and determine if the new one is better.
        
        Args:
            new_selector: The new selector to evaluate.
            existing_selector: The existing selector to compare against.
            
        Returns:
            True if the new selector is better, False otherwise.
        """
        # Prefer ID selectors
        if new_selector.startswith('#') and not existing_selector.startswith('#'):
            return True
            
        # Prefer more specific selectors (more elements in the path)
        new_specificity = self._calculate_selector_specificity(new_selector)
        existing_specificity = self._calculate_selector_specificity(existing_selector)
        
        if new_specificity > existing_specificity:
            return True
            
        # Prefer shorter selectors when specificity is the same
        if new_specificity == existing_specificity and len(new_selector) < len(existing_selector):
            return True
            
        return False
    
    def _calculate_selector_specificity(self, selector: str) -> int:
        """
        Calculate the specificity of a CSS selector.
        
        Args:
            selector: The CSS selector to evaluate.
            
        Returns:
            The specificity score of the selector.
        """
        # Count elements that contribute to specificity
        specificity = 0
        
        # ID selectors (highest specificity)
        specificity += selector.count('#') * 100
        
        # Class selectors and attribute selectors
        specificity += selector.count('.') * 10
        specificity += selector.count('[') * 10
        
        # Element selectors
        specificity += len([c for c in selector.split(' ') if c and not c.startswith('#') and not c.startswith('.') and '[' not in c])
        
        return specificity
    
    def _is_better_attribute(self, new_attr: str, existing_attr: str) -> bool:
        """
        Determine if a new attribute is better than an existing one.
        
        Args:
            new_attr: The new attribute to evaluate.
            existing_attr: The existing attribute to compare against.
            
        Returns:
            True if the new attribute is better, False otherwise.
        """
        # Define priority order of attributes
        attr_priority = {
            "content": 5,  # Often contains clean data from meta tags
            "itemprop": 4, # Structured data attribute
            "data-price": 4, # Specific data attributes
            "data-id": 4,
            "data-sku": 4,
            "src": 3,      # For images
            "href": 2,     # For links
            "alt": 1,      # For image descriptions
            "text": 0      # Default extraction
        }
        
        # Get priority values, defaulting to 0
        new_priority = attr_priority.get(new_attr, 0)
        existing_priority = attr_priority.get(existing_attr, 0)
        
        # Higher priority wins
        return new_priority > existing_priority


def merge_schemas(schemas: List[Dict[str, Any]], quality_threshold: float = 0.6) -> Dict[str, Any]:
    """
    Merge multiple extraction schemas into an optimized schema.
    
    Args:
        schemas: List of schemas to merge.
        quality_threshold: Minimum quality score for inclusion in the merged schema.
        
    Returns:
        A merged schema optimized for extraction accuracy.
    """
    merger = SchemaMerger(quality_threshold=quality_threshold)
    return merger.merge(schemas)


def enhance_schema_with_feedback(
    schema: Dict[str, Any], 
    successful_fields: List[str],
    failed_fields: List[str]
) -> Dict[str, Any]:
    """
    Enhance a schema based on extraction feedback.
    
    Args:
        schema: The schema to enhance.
        successful_fields: List of field names that were successfully extracted.
        failed_fields: List of field names that failed extraction.
        
    Returns:
        An enhanced schema based on the feedback.
    """
    # Create a copy of the schema to modify
    enhanced_schema = {"fields": []}
    
    # Track fields for modification
    fields_to_keep = set(successful_fields)
    fields_to_modify = set(failed_fields)
    
    # Process each field
    for field_data in schema.get("fields", []):
        field_name = field_data.get("name", "")
        
        if field_name in fields_to_keep:
            # Keep successful fields as is
            enhanced_schema["fields"].append(field_data.copy())
        elif field_name in fields_to_modify:
            # Mark failed fields for review or modification
            field_copy = field_data.copy()
            field_copy["needs_review"] = True
            enhanced_schema["fields"].append(field_copy)
        else:
            # Include other fields unchanged
            enhanced_schema["fields"].append(field_data.copy())
    
    # Validate and correct the enhanced schema
    validator = SchemaValidator()
    is_valid, _ = validator.validate(enhanced_schema)
    if not is_valid:
        return validator.correct_schema(enhanced_schema)
        
    return enhanced_schema


def optimize_schema_for_site(
    schema: Dict[str, Any],
    site_url: str,
    extraction_success_rate: float
) -> Dict[str, Any]:
    """
    Optimize a schema for a particular site based on past extraction performance.
    
    Args:
        schema: The schema to optimize.
        site_url: The URL of the site to optimize for.
        extraction_success_rate: The success rate of past extractions (0-1).
        
    Returns:
        An optimized schema for the site.
    """
    # For now, just validate and correct the schema
    # In a more advanced implementation, this could use site-specific patterns
    validator = SchemaValidator()
    is_valid, _ = validator.validate(schema)
    
    if not is_valid or extraction_success_rate < 0.8:
        return validator.correct_schema(schema)
        
    return schema 