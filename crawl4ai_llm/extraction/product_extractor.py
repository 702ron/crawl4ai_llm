"""
Product extractor to fetch and extract data from e-commerce pages.
"""

import logging
import json
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime
import re

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from pydantic import ValidationError

from ..models import ProductData, ProductPrice, ProductImage
from ..crawler.base import BaseCrawler
from ..crawler.content_filter import ContentFilter
from ..config import config
from .schema_generator import SchemaGenerator
from ..prompts.product_extraction import LLM_EXTRACTION_PROMPT, FALLBACK_EXTRACTION_PROMPT

# Set up logging
logger = logging.getLogger(__name__)


class ProductExtractor:
    """Extracts product information from e-commerce websites."""
    
    def __init__(
        self,
        schema_generator: Optional[SchemaGenerator] = None,
        crawler: Optional[BaseCrawler] = None
    ):
        """
        Initialize the product extractor.
        
        Args:
            schema_generator: An instance of the schema generator.
            crawler: An instance of the base crawler.
        """
        self.schema_generator = schema_generator or SchemaGenerator()
        self.crawler = crawler or BaseCrawler()
        
    def _get_crawler_with_filters(self, additional_filters: Optional[List[ContentFilter]] = None) -> BaseCrawler:
        """
        Get a crawler with combined content filters.
        
        Args:
            additional_filters: Additional content filters to apply.
            
        Returns:
            BaseCrawler: A crawler instance with the combined filters.
        """
        if not additional_filters:
            return self.crawler
            
        # Create a new crawler with the combined filters
        combined_filters = self.crawler.content_filters or []
        combined_filters.extend(additional_filters)
        
        return BaseCrawler(
            headless=self.crawler.headless,
            cache_mode=self.crawler.cache_mode,
            user_agent=self.crawler.user_agent,
            timeout=self.crawler.timeout,
            content_filters=combined_filters
        )
    
    async def extract_with_auto_schema(
        self,
        url: str,
        use_cached_schema: bool = True,
        content_filters: Optional[List[ContentFilter]] = None,
        auto_correct_schema: bool = True
    ) -> ProductData:
        """
        Extract product data using automatically generated schema.
        
        Args:
            url: URL of the product page.
            use_cached_schema: Whether to use cached schema if available.
            content_filters: Optional additional content filters to apply for this extraction.
            auto_correct_schema: Whether to automatically correct invalid schemas.
            
        Returns:
            ProductData: Extracted product information.
        """
        logger.info(f"Extracting product data with auto schema from {url}")
        
        # Use temporary crawler with combined content filters if additional ones are provided
        crawler = self._get_crawler_with_filters(content_filters)
        
        # First, perform basic crawl to get HTML
        crawl_result = await crawler.crawl(url)
        
        if not crawl_result["success"]:
            logger.error(f"Failed to crawl {url}: {crawl_result.get('error')}")
            return ProductData(
                title="Extraction Failed",
                price={"current_price": 0.0, "currency": "USD"},
                extraction_success=False,
                source=url,
                extracted_at=datetime.now().isoformat()
            )
        
        # Generate schema for the product page
        # If the crawler used content filtering, we'll have filtered content in extracted_content
        html_content = crawl_result["html"]
        filtered_content = crawl_result.get("extracted_content")
        
        # Use filtered content if available, otherwise use original HTML
        schema_html = filtered_content[0] if filtered_content and isinstance(filtered_content, list) and filtered_content else html_content
        
        schema = await self.schema_generator.generate_schema(
            url=url,
            html=schema_html,
            use_cache=use_cached_schema,
            auto_correct=auto_correct_schema
        )
        
        # Create extraction strategy with the generated schema
        extraction_strategy = JsonCssExtractionStrategy(schema=schema)
        
        # Perform extraction with generated schema
        result = await crawler.crawl(
            url=url,
            extraction_strategy=extraction_strategy
        )
        
        # Process the result
        if not result["success"] or not result["extracted_content"]:
            logger.error(f"Failed to extract product data from {url}")
            return ProductData(
                title="Extraction Failed",
                price={"current_price": 0.0, "currency": "USD"},
                extraction_success=False,
                source=url,
                extracted_at=datetime.now().isoformat()
            )
            
        try:
            # Convert extracted content to ProductData
            product_data_dict = self._convert_extracted_content_to_product_data(result["extracted_content"], url)
            return ProductData(**product_data_dict)
        except Exception as e:
            logger.error(f"Error converting extracted content to ProductData: {str(e)}")
            return ProductData(
                title=result["extracted_content"].get("title", "Unknown Product"),
                price={"current_price": 0.0, "currency": "USD"},
                raw_data=result["extracted_content"],
                extraction_success=False,
                source=url,
                extracted_at=datetime.now().isoformat()
            )
            
    async def extract_with_llm(
        self,
        url: str,
        fallback: bool = False,
        content_filters: Optional[List[ContentFilter]] = None
    ) -> ProductData:
        """
        Extract product data using LLM extraction.
        
        Args:
            url: URL of the product page.
            fallback: Whether this is being used as a fallback method.
            content_filters: Optional additional content filters to apply for this extraction.
            
        Returns:
            ProductData: Extracted product information.
        """
        logger.info(f"Extracting product data with LLM from {url}")
        
        # Use temporary crawler with combined content filters if additional ones are provided
        crawler = self._get_crawler_with_filters(content_filters)
        
        # First, perform basic crawl to get HTML
        result = await crawler.crawl(url)
        
        if not result["success"]:
            logger.error(f"Failed to crawl {url}: {result.get('error')}")
            return ProductData(
                title="Extraction Failed",
                price={"current_price": 0.0, "currency": "USD"},
                extraction_success=False,
                source=url,
                extracted_at=datetime.now().isoformat()
            )
        
        html_content = result["html"]
        filtered_content = result.get("extracted_content")
        
        # Use filtered content if available, otherwise use original HTML
        content_to_process = filtered_content[0] if filtered_content and isinstance(filtered_content, list) and filtered_content else html_content
        
        # Set up LLM extraction parameters
        provider = f"{config.llm.provider}/{config.llm.model}"
        prompt = FALLBACK_EXTRACTION_PROMPT if fallback else LLM_EXTRACTION_PROMPT
        
        # TODO: Implement LLM extraction using config.llm settings
        # This would typically involve calling an LLM service with the HTML content
        # and processing the response to extract product data
        
        try:
            # For now, we'll return a placeholder response
            # In a real implementation, this would contain the LLM's extracted data
            extracted_content = {
                "title": "LLM Extraction Example",
                "price": 99.99,
                "currency": "USD",
                "description": "This is a placeholder for LLM-extracted content.",
                "extraction_method": "llm"
            }
            
            # Convert extracted content to ProductData
            product_data_dict = self._convert_extracted_content_to_product_data(extracted_content, url)
            return ProductData(**product_data_dict)
        except Exception as e:
            logger.error(f"Error processing LLM extraction: {str(e)}")
            return ProductData(
                title="LLM Extraction Failed",
                price={"current_price": 0.0, "currency": "USD"},
                extraction_success=False,
                source=url,
                extracted_at=datetime.now().isoformat()
            )
            
    def _convert_extracted_content_to_product_data(self, extracted_content: Dict[str, Any], url: str) -> Dict[str, Any]:
        """
        Convert extracted content to a ProductData dictionary.
        
        Args:
            extracted_content: The extracted content from the crawler.
            url: The URL of the product page.
            
        Returns:
            Dict[str, Any]: A dictionary that can be used to create a ProductData object.
        """
        product_data_dict = {
            "source": url,
            "extracted_at": datetime.now().isoformat(),
            "extraction_success": True
        }
        
        # Handle title
        if "title" in extracted_content:
            product_data_dict["title"] = extracted_content["title"]
        else:
            product_data_dict["title"] = "Unknown Product"
            logger.warning(f"No title found for {url}")
            
        # Handle description
        if "description" in extracted_content:
            product_data_dict["description"] = extracted_content["description"]
            
        # Handle short description
        if "short_description" in extracted_content:
            product_data_dict["short_description"] = extracted_content["short_description"]
            
        # Handle brand
        if "brand" in extracted_content:
            product_data_dict["brand"] = extracted_content["brand"]
            
        # Handle price
        price_dict = {"current_price": 0.0, "currency": "USD"}
        
        # Direct price mapping
        if "price" in extracted_content and isinstance(extracted_content["price"], dict):
            price_dict.update(extracted_content["price"])
        else:
            # Handle separate price fields with dot notation
            # Current price
            current_price = None
            if "price.current_price" in extracted_content:
                current_price = extracted_content["price.current_price"]
            elif "price" in extracted_content and not isinstance(extracted_content["price"], dict):
                current_price = extracted_content["price"]
                
            if current_price is not None:
                try:
                    # Clean and convert price string to float
                    if isinstance(current_price, str):
                        # Remove currency symbols and commas
                        current_price = re.sub(r'[^\d.,]', '', current_price)
                        # Replace comma with dot for decimal if needed
                        if ',' in current_price and '.' not in current_price:
                            current_price = current_price.replace(',', '.')
                        elif ',' in current_price and '.' in current_price:
                            # Handle formats like 1,234.56
                            current_price = current_price.replace(',', '')
                    price_dict["current_price"] = float(current_price)
                except (ValueError, TypeError):
                    logger.warning(f"Could not convert price to float: {current_price}")
                    
            # Currency
            if "price.currency" in extracted_content:
                price_dict["currency"] = extracted_content["price.currency"]
            elif "currency" in extracted_content:
                price_dict["currency"] = extracted_content["currency"]
                
            # Original price
            if "price.original_price" in extracted_content:
                try:
                    price_dict["original_price"] = float(extracted_content["price.original_price"])
                except (ValueError, TypeError):
                    pass
            elif "original_price" in extracted_content:
                try:
                    price_dict["original_price"] = float(extracted_content["original_price"])
                except (ValueError, TypeError):
                    pass
                    
            # Discount percentage
            if "price.discount_percentage" in extracted_content:
                try:
                    price_dict["discount_percentage"] = float(extracted_content["price.discount_percentage"])
                except (ValueError, TypeError):
                    pass
            elif "discount_percentage" in extracted_content:
                try:
                    price_dict["discount_percentage"] = float(extracted_content["discount_percentage"])
                except (ValueError, TypeError):
                    pass
                    
        product_data_dict["price"] = price_dict
        
        # Handle identifiers
        product_data_dict["sku"] = extracted_content.get("sku")
        product_data_dict["upc"] = extracted_content.get("upc")
        product_data_dict["ean"] = extracted_content.get("ean")
        product_data_dict["isbn"] = extracted_content.get("isbn")
        product_data_dict["mpn"] = extracted_content.get("mpn")
        product_data_dict["gtin"] = extracted_content.get("gtin")
        
        # Handle images
        images = extracted_content.get("images", [])
        if images:
            # If images is a string, try to convert it
            if isinstance(images, str):
                try:
                    # Check if it's a JSON string
                    images_list = json.loads(images)
                    if isinstance(images_list, list):
                        images = images_list
                    else:
                        images = [images]  # Single image URL
                except json.JSONDecodeError:
                    images = [images]  # Single image URL
                    
            # Make sure images is a list
            if not isinstance(images, list):
                images = [images]
                
            product_data_dict["images"] = []
            for img in images:
                if isinstance(img, dict):
                    # Already in the right format
                    image_dict = {
                        "url": img.get("url", ""),
                        "alt_text": img.get("alt_text")
                    }
                    if "position" in img:
                        try:
                            image_dict["position"] = int(img["position"])
                        except (ValueError, TypeError):
                            pass
                    product_data_dict["images"].append(image_dict)
                else:
                    # Just a URL string
                    product_data_dict["images"].append({"url": img})
        
        # Handle additional fields
        product_data_dict["availability"] = extracted_content.get("availability")
        
        # Rating
        if "rating" in extracted_content:
            try:
                product_data_dict["rating"] = float(extracted_content["rating"])
            except (ValueError, TypeError):
                logger.warning(f"Could not convert rating to float: {extracted_content['rating']}")
                
        # Review count
        if "review_count" in extracted_content:
            try:
                product_data_dict["review_count"] = int(extracted_content["review_count"])
            except (ValueError, TypeError):
                logger.warning(f"Could not convert review_count to int: {extracted_content['review_count']}")
                
        # Category
        if "category" in extracted_content:
            category = extracted_content["category"]
            if isinstance(category, str):
                # Split by separator if it's a string
                product_data_dict["category"] = [c.strip() for c in category.split(">")]
            elif isinstance(category, list):
                product_data_dict["category"] = category
                
        # Store raw data for debugging
        if config.app.debug:
            product_data_dict["raw_data"] = extracted_content
            
        # Validate the data before returning
        self._validate_product_data(product_data_dict)
            
        return product_data_dict
        
    def _validate_product_data(self, product_data: Dict[str, Any]) -> None:
        """
        Validate and try to fix product data before creating the ProductData object.
        
        Args:
            product_data: The product data dictionary to validate.
            
        Note:
            This method modifies the product_data dictionary in place.
        """
        # Ensure required fields have valid values
        
        # Title is required and must be a string
        if "title" not in product_data or not product_data["title"]:
            product_data["title"] = "Unknown Product"
        elif not isinstance(product_data["title"], str):
            try:
                product_data["title"] = str(product_data["title"])
            except Exception:
                product_data["title"] = "Unknown Product"
                
        # Price is required
        if "price" not in product_data or not product_data["price"]:
            product_data["price"] = {"current_price": 0.0, "currency": "USD"}
        elif not isinstance(product_data["price"], dict):
            try:
                # Try to convert to float if it's a price value
                price_value = float(product_data["price"])
                product_data["price"] = {"current_price": price_value, "currency": "USD"}
            except (ValueError, TypeError):
                product_data["price"] = {"current_price": 0.0, "currency": "USD"}
                
        # Ensure price has required fields
        price = product_data["price"]
        if "current_price" not in price or price["current_price"] is None:
            price["current_price"] = 0.0
        elif not isinstance(price["current_price"], (int, float)):
            try:
                price["current_price"] = float(price["current_price"])
            except (ValueError, TypeError):
                price["current_price"] = 0.0
                
        if "currency" not in price or not price["currency"]:
            price["currency"] = "USD"
        elif not isinstance(price["currency"], str):
            try:
                price["currency"] = str(price["currency"])
            except Exception:
                price["currency"] = "USD"
                
        # Ensure images are in the right format
        if "images" in product_data and product_data["images"]:
            valid_images = []
            for img in product_data["images"]:
                if isinstance(img, dict) and "url" in img and img["url"]:
                    # Valid image dict with URL
                    valid_images.append(img)
                elif isinstance(img, str) and img:
                    # Just a URL string
                    valid_images.append({"url": img})
            product_data["images"] = valid_images
            
        # Remove None values (except price_dict which was handled separately)
        for key in list(product_data.keys()):
            if product_data[key] is None and key != "price":
                del product_data[key]
                    
    async def extract(
        self,
        url: str,
        strategy: str = "auto_schema",
        fallback: bool = True,
        content_filters: Optional[List[ContentFilter]] = None
    ) -> ProductData:
        """
        Extract product data from a URL using the specified strategy.
        
        Args:
            url: URL of the product page.
            strategy: Extraction strategy to use (auto_schema or llm).
            fallback: Whether to try alternate strategy if primary fails.
            content_filters: Optional content filters to apply.
            
        Returns:
            ProductData: Extracted product information.
        """
        logger.info(f"Extracting product data from {url} using {strategy} strategy")
        
        # Store original crawler to restore it later if needed
        original_crawler = self.crawler
        
        try:
            # Use enhanced crawler if content filters are provided
            if content_filters:
                self.crawler = self._get_crawler_with_filters(content_filters)
                
            if strategy == "auto_schema":
                result = await self.extract_with_auto_schema(url, content_filters=content_filters)
                
                # If extraction was not successful and fallback is enabled, try LLM
                if not result.extraction_success and fallback:
                    logger.info(f"Auto schema extraction failed, falling back to LLM for {url}")
                    result = await self.extract_with_llm(url, fallback=True, content_filters=content_filters)
                    
            elif strategy == "llm":
                result = await self.extract_with_llm(url, content_filters=content_filters)
                
                # If extraction was not successful and fallback is enabled, try auto schema
                if not result.extraction_success and fallback:
                    logger.info(f"LLM extraction failed, falling back to auto schema for {url}")
                    result = await self.extract_with_auto_schema(url, content_filters=content_filters)
                    
            else:
                logger.error(f"Unknown extraction strategy: {strategy}")
                result = ProductData(
                    title=f"Unknown Extraction Strategy: {strategy}",
                    price={"current_price": 0.0, "currency": "USD"},
                    extraction_success=False,
                    source=url,
                    extracted_at=datetime.now().isoformat()
                )
                
            return result
            
        except Exception as e:
            logger.error(f"Error extracting product data from {url}: {str(e)}")
            return ProductData(
                title="Extraction Error",
                price={"current_price": 0.0, "currency": "USD"},
                extraction_success=False,
                source=url,
                extracted_at=datetime.now().isoformat()
            )
            
        finally:
            # Restore original crawler
            self.crawler = original_crawler
 