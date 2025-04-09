"""
Tests for the schema validator module.

This module contains tests for validating, correcting, and improving extraction
schemas to ensure they meet the requirements for successful product extraction.
"""

import pytest
from typing import Dict, List, Any, Optional
from unittest.mock import patch, MagicMock

from crawl4ai_llm.extraction.schema_validator import SchemaField, SchemaValidator
from crawl4ai_llm.extraction.exceptions import SchemaValidationError
from crawl4ai_llm.extraction.schema_validator import (
    validate_schema,
    correct_schema,
    get_schema_improvement_suggestions,
)


class TestSchemaField:
    """Tests for the SchemaField class."""

    def test_valid_schema_field(self):
        """Test creation of a valid schema field."""
        field = SchemaField(
            name="title",
            selector="h1.product-title",
            required=True,
            attribute=None
        )
        assert field.name == "title"
        assert field.selector == "h1.product-title"
        assert field.required is True
        assert field.attribute is None

    def test_invalid_selector(self):
        """Test validation of invalid selectors."""
        with pytest.raises(SchemaValidationError, match="Invalid selector"):
            SchemaField(
                name="title",
                selector="",  # Empty selector is invalid
                required=True
            )

    def test_invalid_field_name(self):
        """Test validation of invalid field names."""
        with pytest.raises(SchemaValidationError, match="Invalid field name"):
            SchemaField(
                name="",  # Empty name is invalid
                selector=".product-title",
                required=True
            )

    def test_optional_field(self):
        """Test creation of an optional field."""
        field = SchemaField(
            name="description",
            selector=".product-description",
            required=False
        )
        assert field.required is False

    def test_field_with_attribute(self):
        """Test creation of a field with an attribute."""
        field = SchemaField(
            name="image",
            selector="img.product-image",
            required=True,
            attribute="src"
        )
        assert field.attribute == "src"


class TestSchemaValidator:
    """Tests for the SchemaValidator class."""

    def test_validate_valid_schema(self):
        """Test validation of a valid schema."""
        schema = {
            "title": {"selector": "h1.product-title", "required": True},
            "price": {"selector": ".product-price", "required": True},
            "description": {"selector": ".product-description", "required": False}
        }
        validator = SchemaValidator(schema)
        
        # Should not raise an exception
        validator.validate()
        
        # Check internal state
        assert validator.is_valid
        assert len(validator.errors) == 0

    def test_validate_invalid_schema(self):
        """Test validation of an invalid schema."""
        # Missing required fields
        schema = {
            "title": {"selector": "", "required": True},  # Invalid selector
            "price": {"selector": ".product-price"}  # Missing required flag
        }
        validator = SchemaValidator(schema)
        
        # Should not raise an exception but collect errors
        validator.validate()
        
        # Check internal state
        assert not validator.is_valid
        assert len(validator.errors) > 0
        
        # Check for specific errors
        assert any("Invalid selector" in error for error in validator.errors)

    def test_validate_schema_structure(self):
        """Test validation of schema structure."""
        # Schema with incorrect structure
        schema = {
            "title": "h1.product-title",  # Missing nested structure
            "price": {"selector": ".product-price", "required": True}
        }
        validator = SchemaValidator(schema)
        
        validator.validate()
        
        assert not validator.is_valid
        assert any("Invalid field structure" in error for error in validator.errors)

    def test_correct_schema(self):
        """Test correction of an invalid schema."""
        schema = {
            "title": {"selector": "", "required": True},  # Invalid selector
            "price": {"selector": ".product-price"}  # Missing required flag
        }
        validator = SchemaValidator(schema)
        
        corrected_schema = validator.correct_schema()
        
        # Validate corrected schema
        assert "title" in corrected_schema
        assert corrected_schema["title"]["selector"] != ""  # Should be corrected
        assert "required" in corrected_schema["price"]  # Should be added

    def test_generate_report_valid_schema(self):
        """Test report generation for a valid schema."""
        schema = {
            "title": {"selector": "h1.product-title", "required": True},
            "price": {"selector": ".product-price", "required": True},
            "description": {"selector": ".product-description", "required": False}
        }
        validator = SchemaValidator(schema)
        
        validator.validate()
        report = validator.generate_report()
        
        assert report["is_valid"] is True
        assert len(report["errors"]) == 0
        assert "quality_score" in report
        assert report["quality_score"] > 0.8  # Expecting high score for valid schema

    def test_generate_report_invalid_schema(self):
        """Test report generation for an invalid schema."""
        schema = {
            "title": {"selector": "", "required": True},
            "price": {"selector": ".product-price"}
        }
        validator = SchemaValidator(schema)
        
        validator.validate()
        report = validator.generate_report()
        
        assert report["is_valid"] is False
        assert len(report["errors"]) > 0
        assert "quality_score" in report
        assert report["quality_score"] < 0.8  # Expecting lower score for invalid schema

    def test_validate_raises_exception(self):
        """Test that validate() raises an exception when raise_exception=True."""
        schema = {
            "title": {"selector": "", "required": True}
        }
        validator = SchemaValidator(schema)
        
        with pytest.raises(SchemaValidationError):
            validator.validate(raise_exception=True)


class TestSchemaValidatorIntegration:
    """Integration tests for SchemaValidator."""

    def test_validate_real_world_schema(self):
        """Test validation with a real-world schema example."""
        schema = {
            "title": {"selector": "h1.product-title", "required": True},
            "price": {"selector": "span.price-value", "required": True, "attribute": "content"},
            "currency": {"selector": "span.price-currency", "required": False},
            "description": {"selector": "div.product-description", "required": False},
            "images": {"selector": "div.product-gallery img", "required": True, "attribute": "src"},
            "brand": {"selector": "span.product-brand", "required": False},
            "sku": {"selector": "span.product-sku", "required": False},
            "availability": {"selector": "div.product-availability", "required": False}
        }
        
        validator = SchemaValidator(schema)
        validator.validate()
        
        assert validator.is_valid
        
        report = validator.generate_report()
        assert report["quality_score"] > 0.9
        assert "field_coverage" in report
        assert report["field_coverage"]["total_fields"] == 8
        assert report["field_coverage"]["required_fields"] == 3

    def test_correct_common_schema_errors(self):
        """Test correction of common schema errors."""
        # Schema with various common errors
        schema = {
            "title": {"selector": "h1", "required": True},  # Valid
            "price": "span.price",  # Wrong structure
            "images": {"selector": "", "required": True},  # Empty selector
            "description": {"selector": "div.description"}  # Missing required flag
        }
        
        validator = SchemaValidator(schema)
        corrected_schema = validator.correct_schema()
        
        # Verify corrections
        assert isinstance(corrected_schema["price"], dict)
        assert "selector" in corrected_schema["price"]
        assert corrected_schema["price"]["selector"] == "span.price"
        
        assert corrected_schema["images"]["selector"] != ""
        
        assert "required" in corrected_schema["description"]
        
        # Validate the corrected schema
        new_validator = SchemaValidator(corrected_schema)
        new_validator.validate()
        assert new_validator.is_valid 

@pytest.fixture
def valid_schema() -> Dict[str, Any]:
    """Return a valid product extraction schema for testing."""
    return {
        "name": "Test Schema",
        "fields": [
            {
                "name": "title",
                "selector": ".product-title",
                "attribute": "text",
                "required": True
            },
            {
                "name": "price",
                "selector": ".product-price",
                "attribute": "text",
                "required": True,
                "price_parsing": {
                    "currency_symbols": ["$", "€"],
                    "decimal_separator": ".",
                    "thousands_separator": ",",
                    "strip_non_numeric": True
                }
            },
            {
                "name": "description",
                "selector": ".product-description",
                "attribute": "text"
            },
            {
                "name": "images",
                "selector": ".product-image",
                "attribute": "src",
                "array": True
            }
        ]
    }


@pytest.fixture
def invalid_schema() -> Dict[str, Any]:
    """Return an invalid product extraction schema for testing."""
    return {
        "name": "Invalid Schema",
        "fields": [
            {
                "name": "title",
                "attribute": "text"  # Missing selector
            },
            {
                "selector": ".product-price"  # Missing name
            },
            {
                "name": "images",
                "selector": ".product-image",
                "attribute": 123  # Invalid attribute type
            },
            {
                "name": "price",
                "selector": ".product-price[",  # Invalid selector
                "price_parsing": "invalid"  # Invalid price parsing
            }
        ]
    }


class TestSchemaValidator:
    """Tests for the SchemaValidator class."""

    def test_init(self):
        """Test validator initialization."""
        validator = SchemaValidator()
        assert validator.strict is False
        
        strict_validator = SchemaValidator(strict=True)
        assert strict_validator.strict is True
    
    def test_validate_schema_valid(self, valid_schema):
        """Test validation of a valid schema."""
        validator = SchemaValidator()
        result = validator.validate_schema(valid_schema)
        assert result is True
        assert len(validator.errors) == 0
    
    def test_validate_schema_invalid(self, invalid_schema):
        """Test validation of an invalid schema."""
        validator = SchemaValidator()
        result = validator.validate_schema(invalid_schema)
        assert result is False
        assert len(validator.errors) > 0
    
    def test_validate_schema_strict(self, invalid_schema):
        """Test validation in strict mode."""
        validator = SchemaValidator(strict=True)
        with pytest.raises(SchemaValidationError):
            validator.validate_schema(invalid_schema)
    
    def test_correct_schema(self, invalid_schema):
        """Test schema correction."""
        validator = SchemaValidator()
        corrected = validator.correct_schema(invalid_schema)
        
        # Check that corrected schema has all required fields
        assert "fields" in corrected
        assert isinstance(corrected["fields"], list)
        
        # Check that field names are correct
        field_names = {field.get("name") for field in corrected["fields"] if "name" in field}
        assert "title" in field_names
        assert "price" in field_names
        
        # Check that required fields have selectors
        for field in corrected["fields"]:
            if "name" in field and field["name"] in ["title", "price"]:
                assert "selector" in field
                assert isinstance(field["selector"], str)
                
        # Validate the corrected schema
        assert validator.validate_schema(corrected)
    
    def test_validate_selector(self):
        """Test CSS selector validation."""
        validator = SchemaValidator()
        
        # Valid selectors
        assert validator.validate_selector(".product-title") is True
        assert validator.validate_selector("div.product-title") is True
        assert validator.validate_selector("div.product-title[data-id]") is True
        assert validator.validate_selector("div.product-title > span") is True
        
        # Invalid selectors
        assert validator.validate_selector("") is False
        assert validator.validate_selector(None) is False
        assert validator.validate_selector(123) is False
        assert validator.validate_selector(".product-title[unclosed") is False
        assert validator.validate_selector("div.product-title'unclosed") is False
    
    def test_suggest_improvements(self, valid_schema):
        """Test schema improvement suggestions."""
        validator = SchemaValidator()
        suggestions = validator.suggest_improvements(valid_schema)
        
        # Check the recommended fields section exists
        assert "recommended_fields" in suggestions
        
        # Test with a schema that has issues
        problem_schema = {
            "name": "Problem Schema",
            "fields": [
                {
                    "name": "title",
                    "selector": "div",  # Too generic
                    "required": True
                },
                {
                    "name": "price",
                    "selector": ".product-price",
                    "required": True
                    # Missing price_parsing
                },
                {
                    "name": "images",
                    "selector": ".product-image"
                    # Missing array=True and attribute
                }
            ]
        }
        
        suggestions = validator.suggest_improvements(problem_schema)
        
        # Check for specific suggestions
        assert "title" in suggestions
        assert any("generic" in suggestion for suggestion in suggestions["title"])
        
        assert "price" in suggestions
        assert any("price parsing" in suggestion.lower() for suggestion in suggestions["price"])
        
        assert "images" in suggestions
        assert any("array: true" in suggestion for suggestion in suggestions["images"])
    
    def test_non_dict_schema(self):
        """Test handling of non-dictionary schemas."""
        validator = SchemaValidator()
        
        # Test with non-dict values
        assert validator.validate_schema(None) is False
        assert validator.validate_schema([]) is False
        assert validator.validate_schema("string") is False
        
        # Test correction of non-dict values
        corrected = validator.correct_schema(None)
        assert isinstance(corrected, dict)
        assert "fields" in corrected
        
        # Corrected schema should include required fields
        field_names = [field.get("name") for field in corrected["fields"]]
        assert "title" in field_names
        assert "price" in field_names


class TestModuleFunctions:
    """Tests for the module-level convenience functions."""
    
    def test_validate_schema_function(self, valid_schema, invalid_schema):
        """Test the validate_schema function."""
        # Test with valid schema
        assert validate_schema(valid_schema) is True
        
        # Test with invalid schema
        assert validate_schema(invalid_schema) is False
        
        # Test with strict validation
        with pytest.raises(SchemaValidationError):
            validate_schema(invalid_schema, strict=True)
    
    def test_correct_schema_function(self, invalid_schema):
        """Test the correct_schema function."""
        corrected = correct_schema(invalid_schema)
        
        # Validate the corrected schema
        assert validate_schema(corrected) is True
    
    def test_get_schema_improvement_suggestions_function(self, valid_schema):
        """Test the get_schema_improvement_suggestions function."""
        suggestions = get_schema_improvement_suggestions(valid_schema)
        
        # Check that suggestions object is a dictionary
        assert isinstance(suggestions, dict)
        assert "recommended_fields" in suggestions


class TestEdgeCases:
    """Tests for edge cases and unusual inputs."""
    
    def test_empty_schema(self):
        """Test handling of empty schemas."""
        validator = SchemaValidator()
        
        # Empty dictionary
        empty_schema = {}
        assert validator.validate_schema(empty_schema) is False
        corrected = validator.correct_schema(empty_schema)
        assert validate_schema(corrected) is True
        
        # Schema with empty fields list
        empty_fields_schema = {"fields": []}
        assert validator.validate_schema(empty_fields_schema) is False
        corrected = validator.correct_schema(empty_fields_schema)
        assert validate_schema(corrected) is True
    
    def test_duplicate_field_names(self):
        """Test handling of duplicate field names."""
        schema = {
            "fields": [
                {"name": "title", "selector": ".title1"},
                {"name": "title", "selector": ".title2"},
                {"name": "price", "selector": ".price"}
            ]
        }
        
        validator = SchemaValidator()
        assert validator.validate_schema(schema) is False
        assert any("Duplicate field" in error for error in validator.errors)
        
        corrected = validator.correct_schema(schema)
        # Should keep only one instance of each field name
        field_names = [field.get("name") for field in corrected["fields"]]
        assert field_names.count("title") == 1
    
    def test_price_parsing_validation(self):
        """Test validation of price parsing configuration."""
        schema = {
            "fields": [
                {"name": "title", "selector": ".title"},
                {
                    "name": "price",
                    "selector": ".price",
                    "price_parsing": {
                        "currency_symbols": "invalid",  # Should be a list
                        "decimal_separator": 123,  # Should be a string
                        "thousands_separator": True,  # Should be a string
                        "strip_non_numeric": "yes"  # Should be a boolean
                    }
                }
            ]
        }
        
        validator = SchemaValidator()
        assert validator.validate_schema(schema) is False
        
        # Check for specific error messages
        assert any("currency_symbols" in error for error in validator.errors)
        assert any("decimal_separator" in error for error in validator.errors)
        assert any("thousands_separator" in error for error in validator.errors)
        assert any("strip_non_numeric" in error for error in validator.errors)
        
        corrected = validator.correct_schema(schema)
        # Should have valid price parsing
        for field in corrected["fields"]:
            if field.get("name") == "price":
                assert "price_parsing" in field
                assert isinstance(field["price_parsing"], dict)
                assert isinstance(field["price_parsing"].get("currency_symbols"), list) 