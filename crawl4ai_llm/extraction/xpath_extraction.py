"""
XPath-based extraction strategy for product data.

This module provides extraction functionality using XPath expressions for e-commerce product data.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from bs4 import BeautifulSoup
from pydantic import ValidationError

try:
    from lxml import etree
    from lxml.html import fromstring
    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False

from ..crawler.base import BaseCrawler
from ..crawler.content_filter import ContentFilter, XPathContentFilter
from ..models import ProductData, ProductImage, ProductPrice, ProductAttribute

# Set up logging
logger = logging.getLogger(__name__)


class XPathExtractor:
    """Extract product information using XPath expressions."""

    def __init__(
        self,
        crawler: Optional[BaseCrawler] = None,
    ):
        """
        Initialize the XPath extractor.

        Args:
            crawler: An instance of the base crawler.
        """
        self.crawler = crawler or BaseCrawler()
        if not LXML_AVAILABLE:
            logger.warning("lxml is not available. XPath extraction will be limited to basic expressions.")

    async def extract_with_xpath(
        self,
        url: str,
        xpath_expressions: Dict[str, str],
        content_filters: Optional[List[ContentFilter]] = None,
    ) -> ProductData:
        """
        Extract product data using XPath expressions.

        Args:
            url: URL of the product page.
            xpath_expressions: Dictionary mapping field names to XPath expressions.
            content_filters: Optional additional content filters to apply.

        Returns:
            ProductData: Extracted product information.
        """
        logger.info(f"Extracting product data with XPath expressions from {url}")

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
        extracted_data = self._extract_fields_with_xpath(html_content, xpath_expressions)
        
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

    def _extract_fields_with_xpath(
        self, html: str, xpath_expressions: Dict[str, Union[str, Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Extract fields from HTML using XPath expressions.

        Args:
            html: HTML content to extract data from.
            xpath_expressions: Dict mapping field names to XPath expressions or field configs.

        Returns:
            Dict with extracted field values.
        """
        if not LXML_AVAILABLE:
            logger.warning("lxml is not available. XPath extraction will be limited.")
            return self._extract_with_basic_xpath(html, xpath_expressions)
            
        try:
            # Parse HTML with lxml
            tree = fromstring(html)
            extracted_data = {}
            
            for field_name, xpath_config in xpath_expressions.items():
                xpath_expr = xpath_config
                attribute = None
                is_array = False
                
                # Handle complex XPath configuration
                if isinstance(xpath_config, dict):
                    xpath_expr = xpath_config.get("xpath", "")
                    attribute = xpath_config.get("attribute")
                    is_array = xpath_config.get("array", False)
                
                if not xpath_expr:
                    continue
                    
                try:
                    # Extract elements using XPath
                    elements = tree.xpath(xpath_expr)
                    
                    if not elements:
                        continue
                        
                    if is_array:
                        # Handle array fields
                        values = []
                        for element in elements:
                            if attribute:
                                # Get specific attribute if specified
                                if isinstance(element, etree._Element) and element.get(attribute):
                                    value = element.get(attribute)
                                    values.append(value)
                            else:
                                # Get text content
                                if isinstance(element, str):
                                    value = element.strip()
                                elif hasattr(element, "text_content"):
                                    value = element.text_content().strip()
                                else:
                                    value = str(element).strip()
                                    
                                if value:
                                    values.append(value)
                        
                        if values:
                            extracted_data[field_name] = values
                    else:
                        # Handle single value fields
                        element = elements[0]
                        
                        if attribute:
                            # Get specific attribute
                            if isinstance(element, etree._Element) and element.get(attribute):
                                value = element.get(attribute)
                            else:
                                continue
                        else:
                            # Get text content
                            if isinstance(element, str):
                                value = element.strip()
                            elif hasattr(element, "text_content"):
                                value = element.text_content().strip()
                            else:
                                value = str(element).strip()
                        
                        if value:
                            # Handle special field types
                            if field_name == "price":
                                # Extract price and currency
                                extracted_data[field_name] = self._extract_price(value)
                            elif field_name == "images":
                                # Create image objects
                                if attribute == "src":
                                    alt = ""
                                    if isinstance(element, etree._Element):
                                        alt = element.get("alt", "")
                                    extracted_data[field_name] = [
                                        {"url": value, "alt_text": alt}
                                    ]
                                else:
                                    extracted_data[field_name] = [{"url": value}]
                            else:
                                extracted_data[field_name] = value
                except Exception as e:
                    logger.error(f"Error extracting {field_name} with XPath: {str(e)}")
            
            # Process special fields
            self._process_special_fields(extracted_data, tree, xpath_expressions)
            
            return extracted_data
        except Exception as e:
            logger.error(f"Error parsing HTML with lxml: {str(e)}")
            return {}
    
    def _extract_with_basic_xpath(
        self, html: str, xpath_expressions: Dict[str, Union[str, Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Extract fields using a basic XPath implementation with BeautifulSoup.
        This is a fallback when lxml is not available.

        Args:
            html: HTML content to extract data from.
            xpath_expressions: Dict mapping field names to XPath expressions or field configs.

        Returns:
            Dict with extracted field values.
        """
        soup = BeautifulSoup(html, "html.parser")
        extracted_data = {}
        
        for field_name, xpath_config in xpath_expressions.items():
            xpath_expr = xpath_config
            attribute = None
            is_array = False
            
            # Handle complex XPath configuration
            if isinstance(xpath_config, dict):
                xpath_expr = xpath_config.get("xpath", "")
                attribute = xpath_config.get("attribute")
                is_array = xpath_config.get("array", False)
            
            if not xpath_expr:
                continue
                
            # Only handle very basic XPath expressions
            if xpath_expr.startswith("//"):
                try:
                    # Extract tag name
                    tag = xpath_expr.split("//")[1].split("[")[0]
                    attrs = {}
                    
                    # Handle simple attribute selectors
                    if "[" in xpath_expr and "]" in xpath_expr:
                        attr_part = xpath_expr.split("[")[1].split("]")[0]
                        if "@" in attr_part and "=" in attr_part:
                            attr_name = attr_part.split("@")[1].split("=")[0]
                            attr_value = attr_part.split("=")[1].strip("'\"")
                            attrs[attr_name] = attr_value
                    
                    # Find elements
                    elements = soup.find_all(tag, attrs)
                    
                    if not elements:
                        continue
                        
                    if is_array:
                        # Handle array fields
                        values = []
                        for element in elements:
                            if attribute:
                                value = element.get(attribute, "")
                            else:
                                value = element.get_text(strip=True)
                                
                            if value:
                                values.append(value)
                        
                        if values:
                            extracted_data[field_name] = values
                    else:
                        # Handle single value fields
                        element = elements[0]
                        
                        if attribute:
                            value = element.get(attribute, "")
                        else:
                            value = element.get_text(strip=True)
                        
                        if value:
                            # Handle special field types
                            if field_name == "price":
                                # Extract price and currency
                                extracted_data[field_name] = self._extract_price(value)
                            elif field_name == "images":
                                # Create image objects
                                if attribute == "src":
                                    extracted_data[field_name] = [
                                        {"url": value, "alt_text": element.get("alt", "")}
                                    ]
                                else:
                                    extracted_data[field_name] = [{"url": value}]
                            else:
                                extracted_data[field_name] = value
                except Exception as e:
                    logger.error(f"Error extracting {field_name} with basic XPath: {str(e)}")
        
        return extracted_data
        
    def _process_special_fields(
        self, 
        extracted_data: Dict[str, Any], 
        tree: Any, 
        xpath_expressions: Dict[str, Any]
    ) -> None:
        """
        Process special fields that need additional handling.
        
        Args:
            extracted_data: The currently extracted data.
            tree: The lxml tree of the HTML.
            xpath_expressions: The XPath configuration dictionary.
        """
        # Handle images if not already processed and images_xpath is provided
        if "images" not in extracted_data and "images_xpath" in xpath_expressions:
            img_xpath = xpath_expressions["images_xpath"]
            images = []
            
            try:
                img_elements = tree.xpath(img_xpath)
                for img in img_elements:
                    if hasattr(img, "get"):
                        src = img.get("src")
                        if src:
                            images.append({
                                "url": src,
                                "alt_text": img.get("alt", "")
                            })
                            
                if images:
                    extracted_data["images"] = images
            except Exception as e:
                logger.error(f"Error processing images: {str(e)}")
                
        # Handle product attributes if XPath is provided
        if "attributes_xpath" in xpath_expressions:
            attr_xpath = xpath_expressions["attributes_xpath"]
            name_xpath = xpath_expressions.get("attribute_name_xpath", ".//th | .//dt | .//*[contains(@class, 'name')]")
            value_xpath = xpath_expressions.get("attribute_value_xpath", ".//td | .//dd | .//*[contains(@class, 'value')]")
            
            attributes = []
            
            try:
                attr_elements = tree.xpath(attr_xpath)
                
                for attr_elem in attr_elements:
                    try:
                        # Find name and value elements
                        name_elem = attr_elem.xpath(name_xpath)
                        value_elem = attr_elem.xpath(value_xpath)
                        
                        if name_elem and value_elem:
                            # Extract text
                            if hasattr(name_elem[0], "text_content"):
                                name = name_elem[0].text_content().strip()
                            else:
                                name = str(name_elem[0]).strip()
                                
                            if hasattr(value_elem[0], "text_content"):
                                value = value_elem[0].text_content().strip()
                            else:
                                value = str(value_elem[0]).strip()
                            
                            if name and value:
                                attributes.append({
                                    "name": name,
                                    "value": value
                                })
                    except Exception as e:
                        logger.error(f"Error processing attribute: {str(e)}")
                        
                if attributes:
                    extracted_data["attributes"] = attributes
            except Exception as e:
                logger.error(f"Error processing attributes: {str(e)}")

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
    def create_default_xpath_expressions(cls) -> Dict[str, Any]:
        """
        Create a dictionary of default XPath expressions for common product fields.

        Returns:
            Dict mapping field names to default XPath expressions.
        """
        return {
            "title": {
                "xpath": "//h1 | //div[contains(@class, 'product-title')] | //*[@itemprop='name']"
            },
            "price": {
                "xpath": "//*[contains(@class, 'price')] | //*[@itemprop='price'] | //div[contains(@class, 'product-price')]"
            },
            "description": {
                "xpath": "//*[contains(@class, 'product-description')] | //*[@itemprop='description'] | //div[contains(@class, 'description')]"
            },
            "brand": {
                "xpath": "//*[contains(@class, 'product-brand')] | //*[@itemprop='brand'] | //div[contains(@class, 'brand')]"
            },
            "sku": {
                "xpath": "//*[contains(@class, 'product-sku')] | //*[@itemprop='sku'] | //div[contains(@class, 'sku')]"
            },
            "images_xpath": "//img[contains(@class, 'product-image')] | //*[@itemprop='image'] | //img[contains(@class, 'product-img')]",
            "attributes_xpath": "//ul[contains(@class, 'product-attributes')]/li | //table[contains(@class, 'product-specs')]/tr | //div[contains(@class, 'product-features')]//div",
            "attribute_name_xpath": ".//span[contains(@class, 'attribute-name')] | .//span[contains(@class, 'spec-name')] | .//th",
            "attribute_value_xpath": ".//span[contains(@class, 'attribute-value')] | .//span[contains(@class, 'spec-value')] | .//td",
            "availability": {
                "xpath": "//*[contains(@class, 'availability')] | //*[@itemprop='availability'] | //div[contains(@class, 'stock')]"
            }
        } 