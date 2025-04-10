"""Schema validation module for product extraction schemas.

This module provides functionality to validate, correct, and improve
schemas used for product data extraction.
"""

import copy
import logging
import re
from typing import Any, Callable, Dict, List, Optional, Set, Union, cast

from cssselect import parser as css_parser

from .exceptions import SchemaValidationError

# Define common product attributes and their default values
COMMON_PRODUCT_ATTRIBUTES = {
    "title": {
        "description": "The product title or name",
        "selector": ".product-title, h1, .product-name",
        "attribute": "text",
        "required": True,
    },
    "price": {
        "description": "The product price",
        "selector": ".product-price, .price, span[itemprop='price']",
        "attribute": "text",
        "required": True,
        "price_parsing": {
            "currency_symbols": ["$", "€", "£", "¥"],
            "decimal_separator": ".",
            "thousands_separator": ",",
            "strip_non_numeric": True,
        },
    },
    "description": {
        "description": "The product description",
        "selector": ".product-description, [itemprop='description'], .description",
        "attribute": "text",
        "required": False,
    },
    "brand": {
        "description": "The product brand",
        "selector": ".product-brand, [itemprop='brand'], .brand",
        "attribute": "text",
        "required": False,
    },
    "images": {
        "description": "The product images",
        "selector": ".product-image, img.product, [itemprop='image']",
        "attribute": "src",
        "array": True,
        "required": False,
    },
    "sku": {
        "description": "The product SKU or identifier",
        "selector": "[itemprop='sku'], .product-sku, .sku",
        "attribute": "text",
        "required": False,
    },
    "availability": {
        "description": "Product availability status",
        "selector": "[itemprop='availability'], .availability-status",
        "attribute": "text",
        "required": False,
    },
}

logger = logging.getLogger(__name__)


class SchemaField:
    """Represents a field in an extraction schema."""

    def __init__(
        self,
        name: str,
        selector: str,
        required: bool = False,
        attribute: Optional[str] = None,
        array: bool = False,
        price_parsing: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
    ):
        """Initialize a schema field.

        Args:
            name: The name of the field
            selector: The CSS selector for the field
            required: Whether the field is required
            attribute: The attribute to extract (e.g., "text", "src")
            array: Whether the field represents multiple values
            price_parsing: Configuration for price parsing
            description: Field description

        Raises:
            SchemaValidationError: If validation fails
        """
        if not name:
            raise SchemaValidationError("Invalid field name")

        if not selector:
            raise SchemaValidationError("Invalid selector")

        self.name = name
        self.selector = selector
        self.required = required
        self.attribute = attribute
        self.array = array
        self.price_parsing = price_parsing
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        """Convert the field to a dictionary.

        Returns:
            The field as a dictionary
        """
        field_dict = {
            "name": self.name,
            "selector": self.selector,
        }

        if self.required:
            field_dict["required"] = True

        if self.attribute:
            field_dict["attribute"] = self.attribute

        if self.array:
            field_dict["array"] = True

        if self.price_parsing:
            field_dict["price_parsing"] = self.price_parsing

        if self.description:
            field_dict["description"] = self.description

        return field_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SchemaField":
        """Create a field from a dictionary.

        Args:
            data: The field data

        Returns:
            A new SchemaField instance
        """
        return cls(
            name=data.get("name", ""),
            selector=data.get("selector", ""),
            required=data.get("required", False),
            attribute=data.get("attribute"),
            array=data.get("array", False),
            price_parsing=data.get("price_parsing"),
            description=data.get("description"),
        )


class SchemaValidator:
    """Validator for product extraction schemas."""

    def __init__(self, schema: Optional[Dict[str, Any]] = None, strict: bool = False):
        """Initialize the schema validator.

        Args:
            schema: Optional schema to validate
            strict: If True, raises exceptions for invalid schemas instead of returning False
        """
        self.schema = schema
        self.strict = strict
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.is_valid = False

    def validate(self, raise_exception: bool = False) -> bool:
        """Validate the schema.

        Args:
            raise_exception: Whether to raise an exception if validation fails

        Returns:
            True if the schema is valid, False otherwise

        Raises:
            SchemaValidationError: If validation fails and raise_exception is True
        """
        if self.schema is None:
            self.errors = ["No schema provided"]
            self.is_valid = False
            if raise_exception:
                raise SchemaValidationError("No schema provided")
            return False

        self.is_valid = self.validate_schema(self.schema)

        if not self.is_valid and raise_exception:
            raise SchemaValidationError("Schema validation failed", self.errors)

        return self.is_valid

    def validate_schema(self, schema: Any) -> bool:
        """Validate a product extraction schema.

        Args:
            schema: The schema to validate

        Returns:
            True if the schema is valid, False otherwise

        Raises:
            SchemaValidationError: If validation fails and strict mode is enabled
        """
        self.errors = []
        self.warnings = []

        # Schema must be a dictionary
        if not isinstance(schema, dict):
            self.errors.append(
                f"Schema must be a dictionary, got {type(schema).__name__}"
            )
            if self.strict:
                raise SchemaValidationError("Invalid schema", self.errors)
            return False

        # Check for fields list or direct field definitions
        if "fields" in schema and isinstance(schema["fields"], list):
            # Schema with fields list
            valid = self._validate_schema_structure(schema)
        else:
            # Schema with direct field definitions
            valid = self._validate_direct_fields_schema(schema)

        if self.errors and self.strict:
            raise SchemaValidationError("Schema validation failed", self.errors)

        return valid

    def _validate_direct_fields_schema(self, schema: Dict[str, Any]) -> bool:
        """Validate a schema with directly defined fields.

        Args:
            schema: Schema with fields defined directly as keys

        Returns:
            True if the schema is valid, False otherwise
        """
        # Get field names (all keys except special ones)
        special_keys = ["name", "description"]
        field_names = [key for key in schema.keys() if key not in special_keys]

        if not field_names:
            self.errors.append("Schema must contain at least one field")
            return False

        # Check for required fields
        required_fields = {"title", "price"}
        missing_fields = required_fields - set(field_names)
        if missing_fields:
            self.errors.append(f"Required fields missing: {', '.join(missing_fields)}")

        # Validate each field
        valid_fields = True
        for name in field_names:
            field_value = schema[name]
            if not isinstance(field_value, dict):
                self.errors.append(
                    f"Field '{name}' must be a dictionary, got {type(field_value).__name__}"
                )
                valid_fields = False
                continue

            # Add name to field dictionary for validation
            field_dict = copy.deepcopy(field_value)
            field_dict["name"] = name

            # Validate field
            if not self._validate_field_dict(field_dict):
                valid_fields = False

        return len(self.errors) == 0 and valid_fields

    def _validate_schema_structure(self, schema: Dict[str, Any]) -> bool:
        """Validate the overall structure of the schema.

        Args:
            schema: The schema to validate

        Returns:
            True if the structure is valid, False otherwise
        """
        if "fields" not in schema:
            self.errors.append("Schema must contain a 'fields' key")
            return False

        if not isinstance(schema["fields"], list):
            self.errors.append(
                f"'fields' must be a list, got {type(schema['fields']).__name__}"
            )
            return False

        if not schema["fields"]:
            self.errors.append("Schema must contain at least one field")
            return False

        # Check for required fields (title and price)
        field_names = {
            field.get("name")
            for field in schema["fields"]
            if isinstance(field, dict) and "name" in field
        }
        required_fields = {"title", "price"}
        missing_fields = required_fields - field_names
        if missing_fields:
            self.errors.append(f"Required fields missing: {', '.join(missing_fields)}")

        # Check for duplicate field names
        duplicate_fields: Set[str] = set()
        field_counts: Dict[str, int] = {}

        for field in schema["fields"]:
            if isinstance(field, dict) and "name" in field:
                name = field["name"]
                field_counts[name] = field_counts.get(name, 0) + 1
                if field_counts[name] > 1:
                    duplicate_fields.add(name)

        if duplicate_fields:
            self.errors.append(
                f"Duplicate field names found: {', '.join(duplicate_fields)}"
            )

        # Validate each field individually
        valid_fields = True
        for i, field in enumerate(schema["fields"]):
            if not self._validate_field(field, i):
                valid_fields = False

        return len(self.errors) == 0 and valid_fields

    def _validate_field(self, field: Any, index: int) -> bool:
        """Validate a single schema field.

        Args:
            field: The field to validate
            index: The index of the field in the schema

        Returns:
            True if the field is valid, False otherwise
        """
        if not isinstance(field, dict):
            self.errors.append(f"Field at index {index} must be a dictionary")
            return False

        # Check for required keys
        if "name" not in field:
            self.errors.append(f"Field at index {index} is missing required 'name' key")
            return False

        return self._validate_field_dict(field)

    def _validate_field_dict(self, field: Dict[str, Any]) -> bool:
        """Validate a field dictionary.

        Args:
            field: Field dictionary with name key

        Returns:
            True if valid, False otherwise
        """
        name = field["name"]

        if not isinstance(name, str):
            self.errors.append(f"Field 'name' must be a string")
            return False

        if "selector" not in field:
            self.errors.append(f"Field '{name}' is missing required 'selector' key")
            return False

        # Validate selector
        if not self.validate_selector(field.get("selector")):
            self.errors.append(
                f"Field '{name}' has invalid CSS selector: {field.get('selector')}"
            )
            return False

        # Validate attribute
        if "attribute" in field and not isinstance(field["attribute"], str):
            self.errors.append(
                f"Field '{name}' has invalid attribute: must be a string"
            )
            return False

        # Validate array flag
        if "array" in field and not isinstance(field["array"], bool):
            self.errors.append(
                f"Field '{name}' has invalid 'array' value: must be a boolean"
            )
            return False

        # Validate required flag
        if "required" in field and not isinstance(field["required"], bool):
            self.errors.append(
                f"Field '{name}' has invalid 'required' value: must be a boolean"
            )
            return False

        # Validate price parsing configuration if present
        if "price_parsing" in field:
            if not self._validate_price_parsing(field["price_parsing"], name):
                return False

        return True

    def _validate_price_parsing(self, config: Any, field_name: str) -> bool:
        """Validate price parsing configuration.

        Args:
            config: The price parsing configuration
            field_name: The name of the field being validated

        Returns:
            True if the configuration is valid, False otherwise
        """
        valid = True

        if not isinstance(config, dict):
            self.errors.append(
                f"Field '{field_name}' has invalid price_parsing: must be a dictionary"
            )
            return False

        # Validate currency_symbols
        if "currency_symbols" in config and not isinstance(
            config["currency_symbols"], list
        ):
            self.errors.append(
                f"Field '{field_name}' has invalid price_parsing.currency_symbols: must be a list"
            )
            valid = False

        # Validate decimal_separator
        if "decimal_separator" in config and not isinstance(
            config["decimal_separator"], str
        ):
            self.errors.append(
                f"Field '{field_name}' has invalid price_parsing.decimal_separator: must be a string"
            )
            valid = False

        # Validate thousands_separator
        if "thousands_separator" in config and not isinstance(
            config["thousands_separator"], str
        ):
            self.errors.append(
                f"Field '{field_name}' has invalid price_parsing.thousands_separator: must be a string"
            )
            valid = False

        # Validate strip_non_numeric
        if "strip_non_numeric" in config and not isinstance(
            config["strip_non_numeric"], bool
        ):
            self.errors.append(
                f"Field '{field_name}' has invalid price_parsing.strip_non_numeric: must be a boolean"
            )
            valid = False

        return valid

    def validate_selector(self, selector: Any) -> bool:
        """Validate a CSS selector.

        Args:
            selector: The selector to validate

        Returns:
            True if the selector is valid, False otherwise
        """
        if not isinstance(selector, str) or not selector:
            return False

        try:
            css_parser.parse(selector)
            return True
        except Exception:
            return False

    def correct_schema(self, schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Attempt to correct an invalid schema.

        Args:
            schema: The schema to correct

        Returns:
            A corrected version of the schema
        """
        if schema is None:
            schema = self.schema

        if not isinstance(schema, dict):
            schema = {}

        # Handle different schema structures
        if "fields" in schema and isinstance(schema["fields"], list):
            # Schema with fields list
            return self._correct_fields_list_schema(schema)
        else:
            # Schema with direct field definitions (or empty schema)
            return self._correct_direct_fields_schema(schema)

    def _correct_direct_fields_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Correct a schema with directly defined fields.

        Args:
            schema: Schema with fields defined directly as keys

        Returns:
            Corrected schema with fields list
        """
        corrected_schema = {
            "name": schema.get("name", "Product Extraction Schema"),
            "fields": [],
        }

        # Get field names (all keys except special ones)
        special_keys = ["name", "description"]
        field_names = [key for key in schema.keys() if key not in special_keys]

        # Convert fields to standardized format
        for name in field_names:
            field_value = schema[name]

            # Handle string values (convert to selector)
            if isinstance(field_value, str):
                field_dict = {
                    "name": name,
                    "selector": field_value,
                    "attribute": "text",
                }

                # Set required for title and price
                if name in ["title", "price"]:
                    field_dict["required"] = True

                # Add price parsing for price field
                if name == "price":
                    field_dict["price_parsing"] = COMMON_PRODUCT_ATTRIBUTES["price"][
                        "price_parsing"
                    ]

                # Set array and src attribute for images
                if name == "images":
                    field_dict["array"] = True
                    field_dict["attribute"] = "src"

                corrected_schema["fields"].append(field_dict)

            # Handle dictionary values
            elif isinstance(field_value, dict):
                field_dict = copy.deepcopy(field_value)
                field_dict["name"] = name

                # Ensure selector is valid
                if "selector" not in field_dict or not self.validate_selector(
                    field_dict["selector"]
                ):
                    if name in COMMON_PRODUCT_ATTRIBUTES:
                        field_dict["selector"] = COMMON_PRODUCT_ATTRIBUTES[name][
                            "selector"
                        ]
                    else:
                        field_dict["selector"] = f".{name}"

                # Ensure attribute is present
                if "attribute" not in field_dict:
                    if name == "images":
                        field_dict["attribute"] = "src"
                    else:
                        field_dict["attribute"] = "text"

                # Ensure required is set for title and price
                if name in ["title", "price"] and "required" not in field_dict:
                    field_dict["required"] = True

                # Add price parsing for price field
                if name == "price" and "price_parsing" not in field_dict:
                    field_dict["price_parsing"] = COMMON_PRODUCT_ATTRIBUTES["price"][
                        "price_parsing"
                    ]

                # Ensure array is set for images
                if name == "images" and "array" not in field_dict:
                    field_dict["array"] = True

                corrected_schema["fields"].append(field_dict)

        # Add missing required fields
        existing_fields = {field["name"] for field in corrected_schema["fields"]}
        for required_name in ["title", "price"]:
            if required_name not in existing_fields:
                field_dict = copy.deepcopy(COMMON_PRODUCT_ATTRIBUTES[required_name])
                field_dict["name"] = required_name
                corrected_schema["fields"].append(field_dict)

        return corrected_schema

    def _correct_fields_list_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Correct a schema with a fields list.

        Args:
            schema: Schema with a fields list

        Returns:
            Corrected schema
        """
        corrected_schema = copy.deepcopy(schema)

        # Ensure we have a fields list
        if "fields" not in corrected_schema:
            corrected_schema["fields"] = []

        if not isinstance(corrected_schema["fields"], list):
            corrected_schema["fields"] = []

        # Track field names to avoid duplicates
        field_names: Set[str] = set()
        corrected_fields = []

        for field in corrected_schema["fields"]:
            if not isinstance(field, dict):
                continue

            # Skip fields without a name
            if "name" not in field or not isinstance(field["name"], str):
                continue

            # Handle duplicate fields (keep the first occurrence)
            if field["name"] in field_names:
                continue

            field_names.add(field["name"])

            # Ensure the field has a valid selector
            if "selector" not in field or not self.validate_selector(field["selector"]):
                # Try to get a default selector from common product attributes
                if field["name"] in COMMON_PRODUCT_ATTRIBUTES:
                    field["selector"] = COMMON_PRODUCT_ATTRIBUTES[field["name"]][
                        "selector"
                    ]
                else:
                    field["selector"] = f".{field['name']}"

            # Ensure attribute is present
            if "attribute" not in field or not isinstance(field["attribute"], str):
                field["attribute"] = "text"

            # Correct price parsing if needed
            if field["name"] == "price" and (
                "price_parsing" not in field
                or not isinstance(field["price_parsing"], dict)
            ):
                field["price_parsing"] = COMMON_PRODUCT_ATTRIBUTES["price"][
                    "price_parsing"
                ]
            elif "price_parsing" in field and isinstance(field["price_parsing"], dict):
                # Correct price parsing configuration
                price_parsing = field["price_parsing"]

                if "currency_symbols" not in price_parsing or not isinstance(
                    price_parsing["currency_symbols"], list
                ):
                    price_parsing["currency_symbols"] = ["$", "€", "£", "¥"]

                if "decimal_separator" not in price_parsing or not isinstance(
                    price_parsing["decimal_separator"], str
                ):
                    price_parsing["decimal_separator"] = "."

                if "thousands_separator" not in price_parsing or not isinstance(
                    price_parsing["thousands_separator"], str
                ):
                    price_parsing["thousands_separator"] = ","

                if "strip_non_numeric" not in price_parsing or not isinstance(
                    price_parsing["strip_non_numeric"], bool
                ):
                    price_parsing["strip_non_numeric"] = True

            # Correct array flag for image fields
            if field["name"] == "images" and (
                "array" not in field or not isinstance(field["array"], bool)
            ):
                field["array"] = True

            corrected_fields.append(field)

        # Ensure required fields are present
        required_fields = {"title", "price"}
        existing_fields = {field["name"] for field in corrected_fields}

        for field_name in required_fields - existing_fields:
            if field_name in COMMON_PRODUCT_ATTRIBUTES:
                field_dict = copy.deepcopy(COMMON_PRODUCT_ATTRIBUTES[field_name])
                field_dict["name"] = field_name
                corrected_fields.append(field_dict)

        corrected_schema["fields"] = corrected_fields

        # Add schema name if missing
        if "name" not in corrected_schema or not isinstance(
            corrected_schema["name"], str
        ):
            corrected_schema["name"] = "Product Extraction Schema"

        return corrected_schema

    def generate_report(self) -> Dict[str, Any]:
        """Generate a quality report for the schema.

        Returns:
            A report containing quality metrics and suggestions
        """
        # Validate the schema first if not already validated
        if self.schema is None:
            return {
                "is_valid": False,
                "errors": ["No schema provided"],
                "quality_score": 0.0,
                "suggestions": {},
            }

        if not hasattr(self, "is_valid") or self.errors is None:
            self.validate()

        report = {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "quality_score": 0.5 if self.is_valid else 0.0,
            "suggestions": self.suggest_improvements(self.schema),
        }

        # Calculate field coverage
        if isinstance(self.schema, dict):
            fields = []
            if "fields" in self.schema and isinstance(self.schema["fields"], list):
                fields = self.schema["fields"]
            else:
                # Handle direct field definitions
                special_keys = ["name", "description"]
                field_names = [
                    key for key in self.schema.keys() if key not in special_keys
                ]
                fields = []
                for name in field_names:
                    field_dict = {"name": name}
                    if name in ["title", "price"]:
                        field_dict["required"] = True
                    if isinstance(self.schema[name], dict):
                        field_dict.update(self.schema[name])
                    fields.append(field_dict)

            required_fields = [
                f for f in fields if isinstance(f, dict) and f.get("required") is True
            ]

            report["field_coverage"] = {
                "total_fields": len(fields),
                "required_fields": len(required_fields),
            }

            # Adjust quality score based on field coverage
            common_fields = set(COMMON_PRODUCT_ATTRIBUTES.keys())
            schema_fields = {
                f.get("name") for f in fields if isinstance(f, dict) and "name" in f
            }

            coverage_ratio = len(schema_fields & common_fields) / len(common_fields)
            report["quality_score"] += coverage_ratio * 0.5

        return report

    def suggest_improvements(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest improvements for a schema.

        Args:
            schema: The schema to analyze

        Returns:
            Dictionary of improvement suggestions by field
        """
        suggestions: Dict[str, List[str]] = {}

        # Get field names from schema (handling both formats)
        field_names = set()
        fields = []

        if "fields" in schema and isinstance(schema["fields"], list):
            # Schema with fields list
            fields = schema["fields"]
            field_names = {
                field.get("name")
                for field in fields
                if isinstance(field, dict) and "name" in field
            }
        else:
            # Schema with direct field definitions
            special_keys = ["name", "description"]
            field_names = {key for key in schema.keys() if key not in special_keys}
            fields = []
            for name in field_names:
                if isinstance(schema[name], dict):
                    field_dict = copy.deepcopy(schema[name])
                    field_dict["name"] = name
                    fields.append(field_dict)
                else:
                    fields.append({"name": name, "selector": schema[name]})

        # Check for missing common fields
        missing_common_fields = set(COMMON_PRODUCT_ATTRIBUTES.keys()) - field_names

        # Add a recommended fields section
        suggestions["recommended_fields"] = [
            f"{field}: {COMMON_PRODUCT_ATTRIBUTES[field]['description']}"
            for field in missing_common_fields
        ]

        # Check each field for potential improvements
        for field in fields:
            if not isinstance(field, dict) or "name" not in field:
                continue

            field_name = field["name"]
            field_suggestions = []

            # Check for overly generic selectors
            if "selector" in field and isinstance(field["selector"], str):
                if field["selector"] in ["div", "span", "p", "body", "html", "*"]:
                    field_suggestions.append(
                        f"Selector '{field['selector']}' is too generic. Consider using a more specific selector."
                    )

            # Check price field for price parsing
            if field_name == "price" and "price_parsing" not in field:
                field_suggestions.append(
                    "Add price_parsing configuration to handle currency symbols and number formatting."
                )

            # Check image field for array flag
            if field_name == "images" and (
                "array" not in field or not field.get("array")
            ):
                field_suggestions.append(
                    "Set 'array: true' for the images field to capture multiple product images."
                )

            # Check for missing attribute
            if "attribute" not in field:
                if field_name == "images":
                    field_suggestions.append(
                        "Add 'attribute: \"src\"' to extract image URLs."
                    )
                else:
                    field_suggestions.append(
                        "Add 'attribute: \"text\"' to extract text content."
                    )

            # Add suggestions if any were found
            if field_suggestions:
                suggestions[field_name] = field_suggestions

        return suggestions

    def _calculate_quality_score(self, schema: Dict[str, Any]) -> float:
        """Calculate a quality score for a schema.

        Args:
            schema: The schema to evaluate

        Returns:
            A score between 0 and 1 indicating schema quality
        """
        score = 0.0
        field_scores = []
        
        # Check for required fields
        fields = schema.get("fields", [])
        if not fields:
            return 0.0
            
        # Process fields in schemas with fields list
        if isinstance(fields, list):
            field_names = [field.get("name", "") for field in fields if isinstance(field, dict)]
            
            # Score each field
            for field in fields:
                if not isinstance(field, dict):
                    continue
                    
                field_score = 0.0
                
                # Base score for having a name and selector
                if field.get("name") and field.get("selector"):
                    field_score += 0.5
                    
                # Better score for required fields
                if field.get("name") in ["title", "price"] and field.get("required", False):
                    field_score += 0.1
                    
                # Better score for detailed selectors
                selector = field.get("selector", "")
                if selector and len(selector) > 5:
                    field_score += 0.1
                    
                # Better score for having attribute specified
                if "attribute" in field:
                    field_score += 0.1
                    
                # Better score for price parsing config
                if field.get("name") == "price" and isinstance(field.get("price_parsing"), dict):
                    field_score += 0.2
                    
                field_scores.append(field_score)
        
        # Calculate average field score
        if field_scores:
            score = sum(field_scores) / len(field_scores)
            
        # Adjust based on coverage of common fields
        common_fields = set(COMMON_PRODUCT_ATTRIBUTES.keys())
        if isinstance(fields, list):
            present_fields = set(field.get("name", "") for field in fields if isinstance(field, dict))
            coverage = len(present_fields.intersection(common_fields)) / len(common_fields)
            score = score * 0.7 + coverage * 0.3
            
        return min(1.0, max(0.0, score))


# Convenience functions
def validate_schema(schema: Dict[str, Any], strict: bool = False) -> bool:
    """Validate a product extraction schema.

    Args:
        schema: The schema to validate
        strict: If True, raises exceptions for invalid schemas

    Returns:
        True if the schema is valid, False otherwise

    Raises:
        SchemaValidationError: If validation fails and strict is True
    """
    validator = SchemaValidator(strict=strict)
    return validator.validate_schema(schema)


def correct_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Correct an invalid schema.

    Args:
        schema: The schema to correct

    Returns:
        A corrected version of the schema
    """
    validator = SchemaValidator()
    return validator.correct_schema(schema)


def get_schema_improvement_suggestions(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Get suggestions for improving a schema.

    Args:
        schema: The schema to analyze

    Returns:
        Dictionary of improvement suggestions by field
    """
    validator = SchemaValidator()
    return validator.suggest_improvements(schema)


# Aliases for backward compatibility
validate_extraction_schema = validate_schema
correct_extraction_schema = correct_schema

# Export list for clarity
__all__ = [
    "SchemaField",
    "SchemaValidator",
    "SchemaValidationError",
    "COMMON_PRODUCT_ATTRIBUTES",
    "validate_schema",
    "correct_schema",
    "get_schema_improvement_suggestions",
    "validate_extraction_schema",
    "correct_extraction_schema",
]
