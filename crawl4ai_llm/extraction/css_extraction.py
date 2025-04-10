"""
CSS-based extraction strategy for product data.

This module provides extraction functionality using CSS selectors for e-commerce product data.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from bs4 import BeautifulSoup
from pydantic import ValidationError

from ..crawler.base import BaseCrawler
from ..crawler.content_filter import ContentFilter, CSSContentFilter
from ..models import ProductData, ProductImage, ProductPrice, ProductAttribute

# Set up logging
logger = logging.getLogger(__name__)


class CSSExtractor:
    """Extract product information using CSS selectors."""

    def __init__(
        self,
        crawler: Optional[BaseCrawler] = None,
    ):
        """
        Initialize the CSS extractor.

        Args:
            crawler: An instance of the base crawler.
        """
        self.crawler = crawler or BaseCrawler()

    async def extract_with_css(
        self,
        url: str,
        selectors: Dict[str, str],
        content_filters: Optional[List[ContentFilter]] = None,
    ) -> ProductData:
        """
        Extract product data using CSS selectors.

        Args:
            url: URL of the product page.
            selectors: Dictionary mapping field names to CSS selectors.
            content_filters: Optional additional content filters to apply.

        Returns:
            ProductData: Extracted product information.
        """
        logger.info(f"Extracting product data with CSS selectors from {url}")

        # Create a combined crawler if content filters are provided
        crawler = self._get_crawler_with_filters(content_filters) if content_filters else self.crawler

        # Crawl the page
        result = await crawler.crawl(url)

        if not result["success"]:
            logger.error(f"Failed to crawl {url}: {result.get('error')}")
            return ProductData(
                title="Extraction Failed",
                price={"current_price": 0.0, "currency": "USD"},
                extraction_success=False,
                source=url,
                extracted_at=datetime.now().isoformat(),
            )

        # Parse HTML
        html_content = result["html"]
        extracted_data = self._extract_fields_with_selectors(html_content, selectors)
        
        # Add source and timestamp
        extracted_data["source"] = url
        extracted_data["extracted_at"] = datetime.now().isoformat()
        extracted_data["extraction_success"] = len(extracted_data) > 2  # More than just source and timestamp
        
        try:
            return ProductData(**extracted_data)
        except ValidationError as e:
            logger.error(f"Error creating ProductData: {str(e)}")
            return ProductData(
                title=extracted_data.get("title", "Extraction Failed"),
                price=extracted_data.get("price", {"current_price": 0.0, "currency": "USD"}),
                extraction_success=False,
                source=url,
                raw_data=extracted_data,
                extracted_at=datetime.now().isoformat(),
            )

    def _extract_fields_with_selectors(
        self, html: str, selectors: Dict[str, Union[str, Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Extract fields from HTML using CSS selectors.

        Args:
            html: HTML content to extract data from.
            selectors: Dict mapping field names to CSS selectors or field configs.

        Returns:
            Dict with extracted field values.
        """
        soup = BeautifulSoup(html, "html.parser")
        extracted_data = {}

        for field_name, selector_config in selectors.items():
            selector = selector_config
            attribute = "text"
            is_array = False
            
            # Handle complex selector configuration
            if isinstance(selector_config, dict):
                selector = selector_config.get("selector", "")
                attribute = selector_config.get("attribute", "text")
                is_array = selector_config.get("array", False)
            
            if not selector:
                continue
                
            try:
                elements = soup.select(selector)
                
                if not elements:
                    continue
                    
                if is_array:
                    # Handle array fields (e.g., images, features)
                    values = []
                    for element in elements:
                        if attribute == "text":
                            value = element.get_text(strip=True)
                        else:
                            value = element.get(attribute, "")
                            
                        if value:
                            values.append(value)
                            
                    if values:
                        extracted_data[field_name] = values
                else:
                    # Handle single value fields
                    element = elements[0]
                    
                    if attribute == "text":
                        value = element.get_text(strip=True)
                    else:
                        value = element.get(attribute, "")
                        
                    if value:
                        # Handle special field types
                        if field_name == "price":
                            # Extract price and currency
                            extracted_data[field_name] = self._extract_price(value)
                        elif field_name == "images":
                            # Create image objects
                            extracted_data[field_name] = [
                                {"url": value, "alt_text": element.get("alt", "")}
                            ]
                        else:
                            extracted_data[field_name] = value
            except Exception as e:
                logger.error(f"Error extracting {field_name}: {str(e)}")
                
        # Process special fields
        self._process_special_fields(extracted_data, soup, selectors)
                
        return extracted_data
        
    def _process_special_fields(
        self, extracted_data: Dict[str, Any], soup: BeautifulSoup, selectors: Dict[str, Any]
    ) -> None:
        """
        Process special fields that need additional handling.
        
        Args:
            extracted_data: The currently extracted data.
            soup: BeautifulSoup object of the HTML.
            selectors: The selector configuration dictionary.
        """
        # Handle images if not already processed
        if "images" not in extracted_data and "images_selector" in selectors:
            img_selector = selectors["images_selector"]
            images = []
            
            for img in soup.select(img_selector):
                src = img.get("src", "")
                if src:
                    images.append({
                        "url": src,
                        "alt_text": img.get("alt", "")
                    })
                    
            if images:
                extracted_data["images"] = images
                
        # Handle product attributes if selector is provided
        if "attributes_selector" in selectors:
            attr_selector = selectors["attributes_selector"]
            attributes = []
            
            for attr_elem in soup.select(attr_selector):
                # Try to find name and value elements within each attribute
                name_elem = attr_elem.select_one(selectors.get("attribute_name_selector", ".attr-name"))
                value_elem = attr_elem.select_one(selectors.get("attribute_value_selector", ".attr-value"))
                
                if name_elem and value_elem:
                    name = name_elem.get_text(strip=True)
                    value = value_elem.get_text(strip=True)
                    
                    if name and value:
                        attributes.append({
                            "name": name,
                            "value": value
                        })
                        
            if attributes:
                extracted_data["attributes"] = attributes

    def _extract_price(self, price_text: str) -> Dict[str, Any]:
        """
        Extract price and currency from a price string.

        Args:
            price_text: String containing price information.

        Returns:
            Dictionary with price and currency information.
        """
        import re
        
        # Default price structure
        price_data = {
            "current_price": 0.0,
            "currency": "USD"
        }
        
        # Remove all whitespace and non-breaking spaces
        price_text = price_text.replace("\xa0", " ").strip()
        
        # Currency symbol detection
        currency_symbols = {
            "$": "USD",
            "€": "EUR",
            "£": "GBP",
            "¥": "JPY",
            "₹": "INR",
            "₽": "RUB",
            "₩": "KRW",
            "A$": "AUD",
            "C$": "CAD",
        }
        
        # Try to detect currency from symbols
        detected_currency = None
        for symbol, code in currency_symbols.items():
            if symbol in price_text:
                detected_currency = code
                # Remove the symbol for easier parsing
                price_text = price_text.replace(symbol, "")
                break
                
        if detected_currency:
            price_data["currency"] = detected_currency
            
        # Try to extract numeric price
        # Handle common price formats
        price_match = re.search(r'(\d+[.,]?\d*)', price_text)
        if price_match:
            price_str = price_match.group(1)
            try:
                # Handle different decimal separators
                if "," in price_str and "." in price_str:
                    # Format like 1,234.56
                    if price_str.find(",") < price_str.find("."):
                        price_str = price_str.replace(",", "")
                    # Format like 1.234,56
                    else:
                        price_str = price_str.replace(".", "").replace(",", ".")
                elif "," in price_str:
                    # Could be either 1,234 or 1,23
                    # If there are exactly 2 digits after comma, assume it's a decimal separator
                    parts = price_str.split(",")
                    if len(parts) == 2 and len(parts[1]) == 2:
                        price_str = price_str.replace(",", ".")
                    else:
                        price_str = price_str.replace(",", "")
                
                price_data["current_price"] = float(price_str)
            except ValueError:
                logger.error(f"Failed to parse price from {price_match.group(1)}")
        
        return price_data

    def _get_crawler_with_filters(
        self, additional_filters: List[ContentFilter]
    ) -> BaseCrawler:
        """
        Get a crawler with combined content filters.

        Args:
            additional_filters: Additional content filters to apply.

        Returns:
            BaseCrawler: A crawler instance with the combined filters.
        """
        # Create a new crawler with the combined filters
        combined_filters = self.crawler.content_filters or []
        combined_filters.extend(additional_filters)

        return BaseCrawler(
            headless=self.crawler.headless,
            cache_mode=self.crawler.cache_mode,
            user_agent=self.crawler.user_agent,
            timeout=self.crawler.timeout,
            content_filters=combined_filters,
        )

    @classmethod
    def create_default_selectors(cls) -> Dict[str, Any]:
        """
        Create a dictionary of default CSS selectors for common product fields.

        Returns:
            Dict mapping field names to default selectors.
        """
        return {
            "title": {
                "selector": "h1, .product-title, .product-name, [itemprop='name']",
                "attribute": "text"
            },
            "price": {
                "selector": ".price, .product-price, [itemprop='price'], .price-current",
                "attribute": "text"
            },
            "description": {
                "selector": ".product-description, [itemprop='description'], .description",
                "attribute": "text"
            },
            "brand": {
                "selector": ".product-brand, [itemprop='brand'], .brand",
                "attribute": "text"
            },
            "sku": {
                "selector": ".product-sku, [itemprop='sku'], .sku",
                "attribute": "text"
            },
            "images_selector": "img.product-image, [itemprop='image'], .product-img",
            "attributes_selector": ".product-attributes li, .product-specs tr, .product-features div",
            "attribute_name_selector": ".attribute-name, .spec-name, th",
            "attribute_value_selector": ".attribute-value, .spec-value, td",
            "availability": {
                "selector": ".availability, .stock, [itemprop='availability']",
                "attribute": "text"
            }
        } 