"""
Module for cleaning and normalizing extracted product data.

This module provides utilities for:
1. Cleaning and normalizing text fields
2. Converting price formats
3. Standardizing units and measurements
4. Handling data validation and enrichment
"""

import logging
import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

from ..models import (ProductAttribute, ProductData, ProductImage,
                      ProductPrice, ProductReview)

logger = logging.getLogger(__name__)


class DataProcessor:
    """
    Handles cleaning, normalizing, and validating extracted product data.

    This class applies a series of transformations to ensure the data meets
    quality standards and is formatted consistently.
    """

    def __init__(
        self,
        currency_symbol_map: Optional[Dict[str, str]] = None,
        unit_conversions: Optional[Dict[str, Dict[str, float]]] = None,
    ):
        """
        Initialize the data processor with optional configuration.

        Args:
            currency_symbol_map: Mapping of currency symbols to ISO currency codes
            unit_conversions: Mapping of unit conversions for standardization
        """
        self.currency_symbol_map = currency_symbol_map or {
            "$": "USD",
            "€": "EUR",
            "£": "GBP",
            "¥": "JPY",
            "₹": "INR",
            "₽": "RUB",
            "₩": "KRW",
            "₿": "BTC",
        }

        self.unit_conversions = unit_conversions or {
            "weight": {"kg": 1.0, "g": 0.001, "lb": 0.453592, "oz": 0.0283495},
            "length": {"m": 1.0, "cm": 0.01, "mm": 0.001, "in": 0.0254, "ft": 0.3048},
            "volume": {
                "l": 1.0,
                "ml": 0.001,
                "gal": 3.78541,
                "oz": 0.0295735,
                "fl oz": 0.0295735,
            },
        }

    def process_product_data(self, product_data: ProductData) -> ProductData:
        """
        Apply all processing steps to a ProductData object.

        Args:
            product_data: The raw extracted product data

        Returns:
            ProductData: Cleaned and normalized product data
        """
        processed_data = product_data.dict()

        # Process text fields
        if processed_data.get("title"):
            processed_data["title"] = self.clean_text(processed_data["title"])

        if processed_data.get("description"):
            processed_data["description"] = self.clean_text(
                processed_data["description"]
            )

        if processed_data.get("brand"):
            processed_data["brand"] = self.clean_text(processed_data["brand"])

        # Process prices
        if processed_data.get("prices"):
            processed_data["prices"] = [
                self._process_price(price) for price in processed_data["prices"]
            ]

        # Process images
        if processed_data.get("images"):
            processed_data["images"] = [
                self._process_image(image) for image in processed_data["images"]
            ]

        # Process attributes
        if processed_data.get("attributes"):
            processed_data["attributes"] = [
                self._process_attribute(attr) for attr in processed_data["attributes"]
            ]

        # Process reviews
        if processed_data.get("reviews"):
            processed_data["reviews"] = [
                self._process_review(review) for review in processed_data["reviews"]
            ]

        # Add metadata
        processed_data["metadata"] = processed_data.get("metadata", {})
        processed_data["metadata"]["processed_at"] = datetime.utcnow().isoformat()
        processed_data["metadata"]["processor_version"] = "1.0.0"

        return ProductData(**processed_data)

    def clean_text(self, text: str) -> str:
        """
        Clean a text field by removing extra whitespace and normalizing characters.

        Args:
            text: The text to clean

        Returns:
            str: Cleaned text
        """
        if not text:
            return ""

        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text.strip())

        # Remove HTML entities and tags
        text = re.sub(r"&[a-zA-Z0-9#]+;", " ", text)
        text = re.sub(r"<[^>]*>", "", text)

        return text.strip()

    def normalize_price(self, price_str: str) -> Dict[str, Any]:
        """
        Extract and normalize price information from a string.

        Args:
            price_str: String containing price information

        Returns:
            Dict with amount and currency information
        """
        price_str = price_str.strip()

        # Extract currency symbol or code
        currency = "USD"  # Default
        for symbol, code in self.currency_symbol_map.items():
            if symbol in price_str:
                currency = code
                price_str = price_str.replace(symbol, "")
                break

        # Extract numeric value
        numeric_str = re.sub(r"[^0-9.,]", "", price_str)

        # Handle different decimal separators
        if "," in numeric_str and "." in numeric_str:
            # Format like 1,234.56
            if numeric_str.rindex(",") < numeric_str.rindex("."):
                numeric_str = numeric_str.replace(",", "")
            # Format like 1.234,56 (European)
            else:
                numeric_str = numeric_str.replace(".", "").replace(",", ".")
        elif "," in numeric_str and not "." in numeric_str:
            # Could be either 1,234 or 1,23
            if len(numeric_str.split(",")[1]) == 2:
                # Likely a decimal separator
                numeric_str = numeric_str.replace(",", ".")
            else:
                # Likely a thousands separator
                numeric_str = numeric_str.replace(",", "")

        try:
            amount = Decimal(numeric_str)
            return {"amount": amount, "currency": currency}
        except:
            logger.warning(f"Could not parse price from '{price_str}'")
            return {"amount": Decimal("0"), "currency": currency}

    def standardize_unit(self, value: str, unit_type: str = None) -> Dict[str, Any]:
        """
        Standardize units of measurement to a common format.

        Args:
            value: The value with unit (e.g., "500g", "2.5 kg")
            unit_type: Optional type hint (weight, length, volume)

        Returns:
            Dict with standardized value and unit
        """
        if not value:
            return {"value": None, "unit": None}

        # Extract numeric value and unit
        match = re.search(r"([\d.,]+)\s*([a-zA-Z]+)", value)
        if not match:
            return {"value": value, "unit": None}

        numeric_str, unit = match.groups()
        numeric_str = numeric_str.replace(",", ".")

        try:
            numeric_value = float(numeric_str)
        except ValueError:
            return {"value": value, "unit": None}

        unit = unit.lower().strip()

        # Determine unit type if not provided
        if unit_type is None:
            for type_name, conversions in self.unit_conversions.items():
                if unit in conversions:
                    unit_type = type_name
                    break

        if unit_type and unit in self.unit_conversions.get(unit_type, {}):
            # Convert to standard unit
            conversion_factor = self.unit_conversions[unit_type][unit]
            standard_value = numeric_value * conversion_factor
            standard_unit = next(
                iter(self.unit_conversions[unit_type])
            )  # Use first unit as standard

            return {
                "value": standard_value,
                "unit": standard_unit,
                "original_value": numeric_value,
                "original_unit": unit,
            }

        return {"value": numeric_value, "unit": unit}

    def _process_price(self, price: Dict[str, Any]) -> Dict[str, Any]:
        """Process and normalize a price object."""
        if isinstance(price, dict):
            price_dict = dict(price)

            # If we have a string amount, try to parse it
            if isinstance(price_dict.get("amount"), str):
                normalized = self.normalize_price(price_dict["amount"])
                price_dict["amount"] = str(normalized["amount"])
                price_dict["currency"] = normalized["currency"]

            return price_dict
        return price

    def _process_image(self, image: Dict[str, Any]) -> Dict[str, Any]:
        """Process and normalize an image object."""
        if isinstance(image, dict):
            image_dict = dict(image)

            # Ensure URL is absolute
            if image_dict.get("url") and not image_dict["url"].startswith(
                ("http://", "https://")
            ):
                if image_dict["url"].startswith("//"):
                    image_dict["url"] = f"https:{image_dict['url']}"
                else:
                    # Can't make this absolute without base URL context
                    pass

            # Clean alt text if present
            if image_dict.get("alt"):
                image_dict["alt"] = self.clean_text(image_dict["alt"])

            return image_dict
        return image

    def _process_attribute(self, attr: Dict[str, Any]) -> Dict[str, Any]:
        """Process and normalize a product attribute."""
        if isinstance(attr, dict):
            attr_dict = dict(attr)

            # Clean name and value
            if attr_dict.get("name"):
                attr_dict["name"] = self.clean_text(attr_dict["name"])

            if attr_dict.get("value") and isinstance(attr_dict["value"], str):
                attr_dict["value"] = self.clean_text(attr_dict["value"])

                # Try to standardize units for attributes that might contain measurements
                if any(
                    unit in attr_dict["value"]
                    for unit_type in self.unit_conversions
                    for unit in self.unit_conversions[unit_type]
                ):
                    standardized = self.standardize_unit(attr_dict["value"])
                    if standardized["unit"]:
                        attr_dict["standardized_value"] = standardized

            return attr_dict
        return attr

    def _process_review(self, review: Dict[str, Any]) -> Dict[str, Any]:
        """Process and normalize a product review."""
        if isinstance(review, dict):
            review_dict = dict(review)

            # Clean text fields
            if review_dict.get("text"):
                review_dict["text"] = self.clean_text(review_dict["text"])

            if review_dict.get("author"):
                review_dict["author"] = self.clean_text(review_dict["author"])

            # Normalize rating to 5-star scale if needed
            if review_dict.get("rating") and review_dict.get("max_rating"):
                try:
                    rating = float(review_dict["rating"])
                    max_rating = float(review_dict["max_rating"])
                    if max_rating != 5.0 and max_rating > 0:
                        normalized_rating = (rating / max_rating) * 5.0
                        review_dict["normalized_rating"] = round(normalized_rating, 1)
                except (ValueError, TypeError):
                    pass

            return review_dict
        return review
