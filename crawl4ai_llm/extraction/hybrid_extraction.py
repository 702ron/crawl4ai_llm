"""
Hybrid extraction strategy combining CSS, XPath, and auto-schema approaches.

This module provides a hybrid approach to product data extraction by combining
multiple extraction strategies for better coverage and accuracy.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from bs4 import BeautifulSoup
from pydantic import ValidationError

from ..crawler.base import BaseCrawler
from ..crawler.content_filter import ContentFilter
from ..models import ProductData, ProductImage, ProductPrice, ProductAttribute
from .css_extraction import CSSExtractor
from .xpath_extraction import XPathExtractor
from .product_extractor import ProductExtractor
from .schema_merger import SchemaMerger

# Set up logging
logger = logging.getLogger(__name__)


class HybridExtractor:
    """
    Extract product information using a hybrid approach of multiple extraction strategies.
    
    This extractor combines CSS selectors, XPath expressions, and auto-schema
    extraction to provide more robust and accurate product data extraction.
    """

    def __init__(
        self,
        css_extractor: Optional[CSSExtractor] = None,
        xpath_extractor: Optional[XPathExtractor] = None,
        auto_extractor: Optional[ProductExtractor] = None,
        crawler: Optional[BaseCrawler] = None,
    ):
        """
        Initialize the hybrid extractor.

        Args:
            css_extractor: An instance of the CSS extractor.
            xpath_extractor: An instance of the XPath extractor.
            auto_extractor: An instance of the auto schema extractor.
            crawler: An instance of the base crawler.
        """
        self.crawler = crawler or BaseCrawler()
        self.css_extractor = css_extractor or CSSExtractor(crawler=self.crawler)
        self.xpath_extractor = xpath_extractor or XPathExtractor(crawler=self.crawler)
        self.auto_extractor = auto_extractor or ProductExtractor(crawler=self.crawler)
        self.schema_merger = SchemaMerger()

    async def extract_with_hybrid(
        self,
        url: str,
        css_selectors: Optional[Dict[str, Any]] = None,
        xpath_expressions: Optional[Dict[str, Any]] = None,
        use_auto_schema: bool = True,
        use_fallback_llm: bool = True,
        content_filters: Optional[List[ContentFilter]] = None,
        extraction_order: Optional[List[str]] = None,
        merge_results: bool = True,
    ) -> ProductData:
        """
        Extract product data using a hybrid approach of multiple extraction strategies.

        Args:
            url: URL of the product page.
            css_selectors: Optional dictionary mapping field names to CSS selectors.
            xpath_expressions: Optional dictionary mapping field names to XPath expressions.
            use_auto_schema: Whether to use auto schema extraction.
            use_fallback_llm: Whether to use LLM extraction as fallback if other methods fail.
            content_filters: Optional additional content filters to apply.
            extraction_order: Order in which to try extraction strategies ["css", "xpath", "auto", "llm"].
            merge_results: Whether to merge results from different strategies or use the first successful one.

        Returns:
            ProductData: Extracted product information.
        """
        logger.info(f"Extracting product data with hybrid approach from {url}")

        # Set default extraction order if not provided
        if extraction_order is None:
            extraction_order = ["auto", "css", "xpath", "llm"]

        # Set default selectors if not provided
        if css_selectors is None and "css" in extraction_order:
            css_selectors = CSSExtractor.create_default_selectors()
            
        if xpath_expressions is None and "xpath" in extraction_order:
            xpath_expressions = XPathExtractor.create_default_xpath_expressions()

        # Initialize results dict
        extraction_results = {}
        successful_extractions = []
        
        # Create a combined crawler if content filters are provided
        crawler = self._get_crawler_with_filters(content_filters) if content_filters else self.crawler

        # First, crawl the page once to get the HTML
        crawl_result = await crawler.crawl(url)
        
        if not crawl_result["success"]:
            logger.error(f"Failed to crawl {url}: {crawl_result.get('error')}")
            return ProductData(
                title="Extraction Failed",
                price={"current_price": 0.0, "currency": "USD"},
                extraction_success=False,
                source=url,
                extracted_at=datetime.now().isoformat(),
            )
            
        html_content = crawl_result["html"]

        # Try extraction strategies in specified order
        for strategy in extraction_order:
            try:
                if strategy == "css" and css_selectors:
                    logger.info(f"Attempting CSS extraction for {url}")
                    css_result = await self.css_extractor.extract_with_css(
                        url, css_selectors, content_filters
                    )
                    
                    if css_result.extraction_success:
                        logger.info(f"CSS extraction successful for {url}")
                        extraction_results["css"] = css_result
                        successful_extractions.append("css")
                        
                        # If merging is disabled, return the first successful result
                        if not merge_results:
                            return css_result
                    else:
                        logger.warning(f"CSS extraction failed for {url}")
                        
                elif strategy == "xpath" and xpath_expressions:
                    logger.info(f"Attempting XPath extraction for {url}")
                    xpath_result = await self.xpath_extractor.extract_with_xpath(
                        url, xpath_expressions, content_filters
                    )
                    
                    if xpath_result.extraction_success:
                        logger.info(f"XPath extraction successful for {url}")
                        extraction_results["xpath"] = xpath_result
                        successful_extractions.append("xpath")
                        
                        # If merging is disabled, return the first successful result
                        if not merge_results:
                            return xpath_result
                    else:
                        logger.warning(f"XPath extraction failed for {url}")
                        
                elif strategy == "auto" and use_auto_schema:
                    logger.info(f"Attempting auto schema extraction for {url}")
                    auto_result = await self.auto_extractor.extract_with_auto_schema(
                        url, content_filters=content_filters
                    )
                    
                    if auto_result.extraction_success:
                        logger.info(f"Auto schema extraction successful for {url}")
                        extraction_results["auto"] = auto_result
                        successful_extractions.append("auto")
                        
                        # If merging is disabled, return the first successful result
                        if not merge_results:
                            return auto_result
                    else:
                        logger.warning(f"Auto schema extraction failed for {url}")
                        
                elif strategy == "llm" and use_fallback_llm:
                    logger.info(f"Attempting LLM extraction for {url}")
                    llm_result = await self.auto_extractor.extract_with_llm(
                        url, content_filters=content_filters
                    )
                    
                    if llm_result.extraction_success:
                        logger.info(f"LLM extraction successful for {url}")
                        extraction_results["llm"] = llm_result
                        successful_extractions.append("llm")
                        
                        # If merging is disabled, return the first successful result
                        if not merge_results:
                            return llm_result
                    else:
                        logger.warning(f"LLM extraction failed for {url}")
                        
            except Exception as e:
                logger.error(f"Error during {strategy} extraction: {str(e)}")

        # If no extraction was successful or merging is enabled with multiple successful extractions
        if not successful_extractions:
            logger.error(f"All extraction methods failed for {url}")
            return ProductData(
                title="Hybrid Extraction Failed",
                price={"current_price": 0.0, "currency": "USD"},
                extraction_success=False,
                source=url,
                extracted_at=datetime.now().isoformat(),
            )
        elif len(successful_extractions) == 1:
            # Only one method was successful
            return extraction_results[successful_extractions[0]]
        else:
            # Multiple methods were successful, merge results
            logger.info(f"Merging results from {', '.join(successful_extractions)} for {url}")
            return self._merge_extraction_results(extraction_results, url)

    def _merge_extraction_results(
        self, extraction_results: Dict[str, ProductData], url: str
    ) -> ProductData:
        """
        Merge extraction results from multiple strategies.

        Args:
            extraction_results: Dictionary mapping strategy names to ProductData objects.
            url: URL of the product page.

        Returns:
            ProductData: Merged product information.
        """
        # Create a merged data dictionary
        merged_data = {}
        
        # Priority order for strategies (first has highest priority in case of conflicts)
        strategy_priority = ["auto", "llm", "css", "xpath"]
        
        # Sort strategies by priority
        strategies = sorted(
            extraction_results.keys(),
            key=lambda x: strategy_priority.index(x) if x in strategy_priority else 999
        )
        
        # Start with the highest priority strategy's data as the base
        if strategies:
            base_product = extraction_results[strategies[0]]
            merged_data = base_product.dict(exclude_none=True)
            
            # Merge additional data from other strategies
            for strategy in strategies[1:]:
                product_data = extraction_results[strategy]
                product_dict = product_data.dict(exclude_none=True)
                
                # Merge each field
                for field, value in product_dict.items():
                    # Skip metadata fields
                    if field in ["source", "extracted_at", "extraction_success", "raw_data"]:
                        continue
                        
                    # Skip empty values
                    if value is None or value == "" or value == [] or value == {}:
                        continue
                        
                    # Handle special case for combining arrays
                    if field in ["images", "attributes"] and isinstance(value, list):
                        if field not in merged_data or not merged_data[field]:
                            merged_data[field] = value
                        else:
                            # For images, combine and deduplicate by URL
                            if field == "images":
                                existing_urls = {img.get("url") for img in merged_data[field]}
                                for img in value:
                                    if img.get("url") and img["url"] not in existing_urls:
                                        merged_data[field].append(img)
                                        existing_urls.add(img["url"])
                            # For attributes, combine and deduplicate by name
                            elif field == "attributes":
                                existing_names = {attr.get("name") for attr in merged_data[field]}
                                for attr in value:
                                    if attr.get("name") and attr["name"] not in existing_names:
                                        merged_data[field].append(attr)
                                        existing_names.add(attr["name"])
                    # Handle special case for price
                    elif field == "price":
                        # Use the price with the most information
                        if field not in merged_data:
                            merged_data[field] = value
                        else:
                            # Count non-empty fields in each price object
                            existing_price_fields = sum(1 for k, v in merged_data[field].items() if v)
                            new_price_fields = sum(1 for k, v in value.items() if v)
                            
                            # Replace if the new one has more information
                            if new_price_fields > existing_price_fields:
                                merged_data[field] = value
                            elif new_price_fields == existing_price_fields:
                                # If both have the same number of fields, use auto or llm over others
                                if strategy in ["auto", "llm"]:
                                    merged_data[field] = value
                    # Simple fields - use the value if it doesn't exist yet
                    elif field not in merged_data or not merged_data[field]:
                        merged_data[field] = value
                    # For text fields, use the longer one (likely more complete)
                    elif isinstance(value, str) and isinstance(merged_data[field], str):
                        if len(value) > len(merged_data[field]):
                            merged_data[field] = value
        
        # Ensure required fields are present
        if "title" not in merged_data or not merged_data["title"]:
            merged_data["title"] = "Hybrid Extraction"
            
        if "price" not in merged_data:
            merged_data["price"] = {"current_price": 0.0, "currency": "USD"}
            
        # Add metadata
        merged_data["source"] = url
        merged_data["extracted_at"] = datetime.now().isoformat()
        merged_data["extraction_success"] = True
        
        try:
            return ProductData(**merged_data)
        except ValidationError as e:
            logger.error(f"Error creating merged ProductData: {str(e)}")
            # Fall back to the highest priority successful extraction
            if strategies:
                return extraction_results[strategies[0]]
            else:
                return ProductData(
                    title="Hybrid Extraction Failed",
                    price={"current_price": 0.0, "currency": "USD"},
                    extraction_success=False,
                    source=url,
                    extracted_at=datetime.now().isoformat(),
                )

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