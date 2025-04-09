"""
Schema enhancer for product extraction.

This module provides functionality to improve extraction schemas based on feedback
from previous extractions and domain-specific knowledge.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass

from .schema_validator import SchemaValidator, COMMON_PRODUCT_FIELDS

logger = logging.getLogger(__name__)

# Feedback types for schema enhancement
EXTRACTION_SUCCESS = "success"  # Field was successfully extracted
EXTRACTION_FAILURE = "failure"  # Field failed to extract
EXTRACTION_PARTIAL = "partial"  # Field was extracted but may be incomplete


@dataclass
class ExtractionFeedback:
    """Represents feedback for a field extraction."""
    field_name: str
    status: str  # One of EXTRACTION_SUCCESS, EXTRACTION_FAILURE, EXTRACTION_PARTIAL
    value: Optional[Any] = None
    error: Optional[str] = None
    suggestions: Optional[List[str]] = None


class SchemaEnhancer:
    """
    Enhances extraction schemas based on feedback and domain knowledge.
    """
    
    def __init__(self, validator: Optional[SchemaValidator] = None):
        """
        Initialize a schema enhancer.
        
        Args:
            validator: Optional schema validator to validate enhanced schemas.
        """
        self.validator = validator or SchemaValidator()
        self.domain_patterns = self._load_domain_patterns()
        
    def enhance_schema(
        self, 
        schema: Dict[str, Any], 
        feedback: List[ExtractionFeedback],
        domain: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enhance a schema based on extraction feedback and domain knowledge.
        
        Args:
            schema: The original schema to enhance.
            feedback: List of feedback objects from previous extractions.
            domain: Optional domain (e.g., 'electronics', 'fashion') for specialized enhancements.
            
        Returns:
            An enhanced schema.
        """
        if not isinstance(schema, dict) or "fields" not in schema:
            logger.warning("Cannot enhance invalid schema")
            return schema
            
        # Create a copy to avoid modifying the original
        enhanced = schema.copy()
        enhanced["fields"] = [f.copy() for f in schema.get("fields", [])]
        
        # Track existing field names
        field_names = {f.get("name", "").lower() for f in enhanced["fields"]}
        
        # Apply feedback-based enhancements
        self._enhance_with_feedback(enhanced, feedback)
        
        # Apply domain-specific enhancements
        if domain:
            self._enhance_for_domain(enhanced, domain, field_names)
            
        # Validate and correct the enhanced schema
        return self.validator.correct_schema(enhanced)
    
    def _enhance_with_feedback(
        self, 
        schema: Dict[str, Any], 
        feedback: List[ExtractionFeedback]
    ) -> None:
        """
        Enhance schema based on extraction feedback.
        
        Args:
            schema: The schema to enhance (modified in-place).
            feedback: Feedback from previous extractions.
        """
        # Group feedback by field
        feedback_by_field = {}
        for fb in feedback:
            if fb.field_name not in feedback_by_field:
                feedback_by_field[fb.field_name] = []
            feedback_by_field[fb.field_name].append(fb)
        
        # Process each field
        for i, field in enumerate(schema["fields"]):
            field_name = field.get("name", "")
            if not field_name or field_name not in feedback_by_field:
                continue
                
            field_feedback = feedback_by_field[field_name]
            success_count = sum(1 for fb in field_feedback if fb.status == EXTRACTION_SUCCESS)
            failure_count = sum(1 for fb in field_feedback if fb.status == EXTRACTION_FAILURE)
            
            # If field extractions are consistently failing, try to improve the selector
            if failure_count > success_count:
                self._improve_failing_field(field, field_feedback)
                
            # If field extractions are partially successful, improve attribute handling
            partial_feedback = [fb for fb in field_feedback if fb.status == EXTRACTION_PARTIAL]
            if partial_feedback:
                self._improve_partial_field(field, partial_feedback)
    
    def _improve_failing_field(
        self, 
        field: Dict[str, Any], 
        feedback: List[ExtractionFeedback]
    ) -> None:
        """
        Improve a field that's consistently failing to extract.
        
        Args:
            field: The field to improve (modified in-place).
            feedback: Feedback for this field.
        """
        field_name = field.get("name", "")
        
        # Try to expand the selector to increase chances of matching
        original_selector = field.get("selector", "")
        if original_selector:
            # Add alternative selectors for common fields
            new_selectors = [original_selector]
            
            if field_name.lower() in {"title", "name", "product_name"}:
                new_selectors.extend([
                    "h1", 
                    ".product-title", 
                    ".product-name", 
                    "[itemprop='name']",
                    "[data-testid='product-title']"
                ])
            elif field_name.lower() in {"price", "current_price", "sale_price"}:
                new_selectors.extend([
                    ".price", 
                    ".product-price", 
                    "[itemprop='price']", 
                    "[data-testid='price']",
                    ".current-price",
                    ".sale-price"
                ])
            elif field_name.lower() in {"description", "product_description"}:
                new_selectors.extend([
                    ".description", 
                    ".product-description", 
                    "[itemprop='description']",
                    "#description",
                    "#product-description"
                ])
            elif field_name.lower() in {"brand", "manufacturer"}:
                new_selectors.extend([
                    ".brand", 
                    ".manufacturer", 
                    "[itemprop='brand']",
                    "[data-testid='brand']"
                ])
            elif field_name.lower() in {"image", "images", "gallery"}:
                new_selectors.extend([
                    ".product-image img", 
                    ".gallery img", 
                    "[itemprop='image']",
                    ".product-gallery img"
                ])
                
                # For images, try different attributes
                if field.get("attribute") == "text":
                    field["attribute"] = "src"
                    
                # Mark as array if it's an image gallery
                if field_name.lower() in {"images", "gallery"}:
                    field["array"] = True
            
            # Add more common attribute variants
            if field.get("attribute") == "text" and field_name.lower() in {"price", "sale_price"}:
                suggested_attributes = ["content", "data-price", "value"]
                for attr in suggested_attributes:
                    new_selectors.append(f"[{attr}]")
            
            # Join unique selectors
            field["selector"] = ", ".join(set(new_selectors))
            
            logger.info(f"Enhanced selector for field '{field_name}' from '{original_selector}' to '{field['selector']}'")
    
    def _improve_partial_field(
        self, 
        field: Dict[str, Any], 
        feedback: List[ExtractionFeedback]
    ) -> None:
        """
        Improve a field that's extracting with partial success.
        
        Args:
            field: The field to improve (modified in-place).
            feedback: Partial success feedback for this field.
        """
        field_name = field.get("name", "")
        
        # Handle special cases for partial extractions
        if field_name.lower() in {"price", "sale_price", "current_price"}:
            # For prices, ensure we're getting the numeric value
            if field.get("attribute") == "text":
                # Add post-processing hint to extract price
                field["post_process"] = "extract_price"
                logger.info(f"Added price post-processing for field '{field_name}'")
                
        elif field_name.lower() in {"images", "gallery"} and not field.get("array"):
            # Mark image collections as arrays
            field["array"] = True
            logger.info(f"Marked field '{field_name}' as array for multiple images")
            
        # Add any suggestions from feedback
        for fb in feedback:
            if fb.suggestions:
                if "alternative_selectors" not in field:
                    field["alternative_selectors"] = []
                field["alternative_selectors"].extend(fb.suggestions)
    
    def _enhance_for_domain(
        self, 
        schema: Dict[str, Any], 
        domain: str,
        existing_fields: Set[str]
    ) -> None:
        """
        Apply domain-specific enhancements to the schema.
        
        Args:
            schema: The schema to enhance (modified in-place).
            domain: The domain to apply enhancements for.
            existing_fields: Set of field names already in the schema.
        """
        patterns = self.domain_patterns.get(domain.lower(), {})
        if not patterns:
            logger.warning(f"No domain patterns available for '{domain}'")
            return
            
        # Add domain-specific fields if they don't exist
        for field_name, field_config in patterns.items():
            if not any(name in existing_fields for name in self._get_field_variations(field_name)):
                schema["fields"].append({
                    "name": field_name,
                    "selector": field_config["selector"],
                    "attribute": field_config.get("attribute", "text"),
                    "required": field_config.get("required", False),
                    "array": field_config.get("array", False),
                    "description": field_config.get("description", f"Domain-specific field for {domain}")
                })
                logger.info(f"Added domain-specific field '{field_name}' for '{domain}'")
    
    def _load_domain_patterns(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Load domain-specific patterns for schema enhancement.
        
        Returns:
            Dictionary mapping domains to field patterns.
        """
        # Domain-specific field patterns
        return {
            "electronics": {
                "specifications": {
                    "selector": ".specifications, .specs, .tech-specs, #specifications, table.specs",
                    "attribute": "text",
                    "array": True,
                    "description": "Technical specifications for electronic products"
                },
                "model_number": {
                    "selector": ".model-number, [itemprop='model'], [data-testid='model-number']",
                    "attribute": "text",
                    "description": "Model number of the electronic product"
                },
                "warranty": {
                    "selector": ".warranty, .warranty-info, [data-testid='warranty']",
                    "attribute": "text",
                    "description": "Warranty information for the product"
                }
            },
            "fashion": {
                "sizes": {
                    "selector": ".sizes, .size-options, [data-testid='size-options'], .size-selector",
                    "attribute": "text",
                    "array": True,
                    "description": "Available sizes for the fashion item"
                },
                "colors": {
                    "selector": ".colors, .color-options, [data-testid='color-options'], .color-selector",
                    "attribute": "text",
                    "array": True,
                    "description": "Available colors for the fashion item"
                },
                "material": {
                    "selector": ".material, [itemprop='material'], [data-testid='material']",
                    "attribute": "text",
                    "description": "Material of the fashion item"
                }
            },
            "grocery": {
                "ingredients": {
                    "selector": ".ingredients, [itemprop='ingredients'], .ingredient-list",
                    "attribute": "text",
                    "description": "Ingredients of the food product"
                },
                "nutrition_facts": {
                    "selector": ".nutrition-facts, .nutrition, .nutrition-info",
                    "attribute": "text",
                    "description": "Nutrition facts for the food product"
                },
                "weight": {
                    "selector": ".weight, .product-weight, [itemprop='weight']",
                    "attribute": "text",
                    "description": "Weight or volume of the food product"
                }
            },
            "furniture": {
                "dimensions": {
                    "selector": ".dimensions, .product-dimensions, [itemprop='height'], [itemprop='width'], [itemprop='depth']",
                    "attribute": "text",
                    "description": "Dimensions of the furniture"
                },
                "assembly_required": {
                    "selector": ".assembly, .assembly-required, [data-testid='assembly']",
                    "attribute": "text",
                    "description": "Whether assembly is required for the furniture"
                },
                "material": {
                    "selector": ".material, [itemprop='material'], [data-testid='material']",
                    "attribute": "text",
                    "description": "Material of the furniture"
                }
            }
        }
    
    def _get_field_variations(self, field_name: str) -> Set[str]:
        """
        Get variations of a field name.
        
        Args:
            field_name: The field name.
            
        Returns:
            Set of field name variations.
        """
        # Normalize the field name
        base_name = field_name.lower()
        
        # Common variations
        variations = {base_name}
        
        # Add underscored versions
        if " " in base_name:
            variations.add(base_name.replace(" ", "_"))
            
        # Add dashed versions
        if " " in base_name or "_" in base_name:
            variations.add(base_name.replace(" ", "-").replace("_", "-"))
            
        # Add camelCase
        if " " in base_name or "_" in base_name or "-" in base_name:
            parts = re.split(r"[ _-]", base_name)
            camel_case = parts[0] + "".join(p.capitalize() for p in parts[1:])
            variations.add(camel_case)
            
        return variations


def enhance_schema_from_results(
    schema: Dict[str, Any],
    successful_extractions: Dict[str, Any],
    failed_extractions: Dict[str, Any],
    domain: Optional[str] = None
) -> Dict[str, Any]:
    """
    Enhance a schema based on successful and failed extraction results.
    
    Args:
        schema: The original schema to enhance.
        successful_extractions: Dictionary mapping field names to successfully extracted values.
        failed_extractions: Dictionary mapping field names to extraction errors.
        domain: Optional domain for specialized enhancements.
        
    Returns:
        An enhanced schema.
    """
    enhancer = SchemaEnhancer()
    
    # Convert extraction results to feedback objects
    feedback = []
    
    for field_name, value in successful_extractions.items():
        status = EXTRACTION_SUCCESS if value else EXTRACTION_PARTIAL
        feedback.append(ExtractionFeedback(field_name=field_name, status=status, value=value))
    
    for field_name, error in failed_extractions.items():
        feedback.append(ExtractionFeedback(field_name=field_name, status=EXTRACTION_FAILURE, error=str(error)))
    
    # Enhance the schema
    return enhancer.enhance_schema(schema, feedback, domain)


def create_adaptive_schema(
    base_schema: Dict[str, Any],
    domain: str,
    site_patterns: Optional[Dict[str, Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Create an adaptive schema that combines base schema with domain and site-specific patterns.
    
    Args:
        base_schema: The base schema to adapt.
        domain: The domain to apply enhancements for.
        site_patterns: Optional dictionary of site-specific patterns.
        
    Returns:
        An adaptive schema.
    """
    enhancer = SchemaEnhancer()
    
    # Start with no feedback to get domain enhancements
    enhanced = enhancer.enhance_schema(base_schema, [], domain)
    
    # Apply site-specific patterns if provided
    if site_patterns:
        existing_fields = {f.get("name", "").lower() for f in enhanced.get("fields", [])}
        
        for field_name, pattern in site_patterns.items():
            if not any(name in existing_fields for name in enhancer._get_field_variations(field_name)):
                enhanced["fields"].append({
                    "name": field_name,
                    "selector": pattern.get("selector", ""),
                    "attribute": pattern.get("attribute", "text"),
                    "required": pattern.get("required", False),
                    "array": pattern.get("array", False),
                    "description": pattern.get("description", f"Site-specific field")
                })
    
    return enhanced 