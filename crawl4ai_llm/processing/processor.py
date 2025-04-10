"""
Module for general content processing functionality.

This module provides tools for processing raw content extracted from web pages,
including filtering, transformation, and structure normalization.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Union

from ..models import ProductData

logger = logging.getLogger(__name__)


class DataProcessingError(Exception):
    """Base exception for errors during data processing operations."""
    pass


class ContentProcessor:
    """
    Processes raw content from web pages for better extraction quality.
    
    This class focuses on preparing content for extraction by removing noise,
    improving structure, and applying content filtering techniques.
    """
    
    def __init__(
        self,
        remove_scripts: bool = True,
        remove_styles: bool = True,
        remove_comments: bool = True,
        clean_whitespace: bool = True,
        min_content_length: int = 50,
    ):
        """
        Initialize the content processor with configuration options.
        
        Args:
            remove_scripts: Whether to remove script tags and their content
            remove_styles: Whether to remove style tags and their content
            remove_comments: Whether to remove HTML comments
            clean_whitespace: Whether to normalize and clean whitespace
            min_content_length: Minimum text length to consider for processing
        """
        self.remove_scripts = remove_scripts
        self.remove_styles = remove_styles
        self.remove_comments = remove_comments
        self.clean_whitespace = clean_whitespace
        self.min_content_length = min_content_length
        
        logger.debug("Initialized ContentProcessor with config: "
                    f"remove_scripts={remove_scripts}, "
                    f"remove_styles={remove_styles}, "
                    f"remove_comments={remove_comments}, "
                    f"clean_whitespace={clean_whitespace}, "
                    f"min_content_length={min_content_length}")
    
    def clean_html(self, html_content: str) -> str:
        """
        Clean HTML content by removing noise elements.
        
        Args:
            html_content: Raw HTML content to clean
            
        Returns:
            Cleaned HTML content
            
        Raises:
            DataProcessingError: If the content is empty or processing fails
        """
        if not html_content:
            raise DataProcessingError("Cannot process empty HTML content")
        
        try:
            content = html_content
            
            # Remove script tags
            if self.remove_scripts:
                content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
            
            # Remove style tags
            if self.remove_styles:
                content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
            
            # Remove comments
            if self.remove_comments:
                content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
            
            # Clean whitespace
            if self.clean_whitespace:
                # Replace multiple whitespace with single space
                content = re.sub(r'\s+', ' ', content)
                # Clean whitespace around tags
                content = re.sub(r'>\s+<', '><', content)
            
            return content
            
        except Exception as e:
            raise DataProcessingError(f"Error cleaning HTML content: {str(e)}")
    
    def extract_main_content(self, html_content: str) -> str:
        """
        Extract the main content area from HTML, removing headers, footers, etc.
        
        This uses heuristics to identify the main content area with the most
        text density and important elements.
        
        Args:
            html_content: HTML content to process
            
        Returns:
            HTML string containing the main content area
        """
        # First clean the HTML
        cleaned_html = self.clean_html(html_content)
        
        # Simple heuristic: look for common content containers
        content_patterns = [
            r'<main[^>]*>(.*?)</main>',
            r'<article[^>]*>(.*?)</article>',
            r'<div[^>]*?class="[^"]*?(?:content|main|product)[^"]*?"[^>]*>(.*?)</div>',
            r'<div[^>]*?id="[^"]*?(?:content|main|product)[^"]*?"[^>]*>(.*?)</div>'
        ]
        
        for pattern in content_patterns:
            matches = re.findall(pattern, cleaned_html, re.DOTALL | re.IGNORECASE)
            if matches:
                # Get the longest match (most likely the main content)
                main_content = max(matches, key=len)
                if len(main_content) >= self.min_content_length:
                    return main_content
        
        # If no main content identified, return the cleaned HTML
        return cleaned_html
    
    def extract_text_blocks(self, html_content: str) -> List[str]:
        """
        Extract meaningful text blocks from HTML content.
        
        Args:
            html_content: HTML content to process
            
        Returns:
            List of text blocks extracted from the content
        """
        # First clean the HTML
        cleaned_html = self.clean_html(html_content)
        
        # Extract text from paragraph tags
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', cleaned_html, re.DOTALL)
        
        # Extract text from heading tags
        headings = []
        for i in range(1, 7):
            h_tags = re.findall(fr'<h{i}[^>]*>(.*?)</h{i}>', cleaned_html, re.DOTALL)
            headings.extend(h_tags)
        
        # Extract text from list items
        list_items = re.findall(r'<li[^>]*>(.*?)</li>', cleaned_html, re.DOTALL)
        
        # Combine all text blocks
        text_blocks = paragraphs + headings + list_items
        
        # Clean individual blocks (remove nested tags, etc.)
        cleaned_blocks = []
        for block in text_blocks:
            # Remove nested HTML tags
            text = re.sub(r'<[^>]*>', '', block)
            # Clean whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            if text and len(text) >= self.min_content_length:
                cleaned_blocks.append(text)
        
        return cleaned_blocks
    
    def remove_boilerplate(self, html_content: str) -> str:
        """
        Remove boilerplate content like navigation, footers, etc.
        
        Args:
            html_content: HTML content to process
            
        Returns:
            HTML with boilerplate elements removed
        """
        content = html_content
        
        # Remove common boilerplate elements by tag or class/id
        boilerplate_patterns = [
            r'<header[^>]*>.*?</header>',
            r'<footer[^>]*>.*?</footer>',
            r'<nav[^>]*>.*?</nav>',
            r'<div[^>]*?class="[^"]*?(?:header|footer|navigation|sidebar|menu|banner|ad)[^"]*?"[^>]*>.*?</div>',
            r'<div[^>]*?id="[^"]*?(?:header|footer|navigation|sidebar|menu|banner|ad)[^"]*?"[^>]*>.*?</div>'
        ]
        
        for pattern in boilerplate_patterns:
            content = re.sub(pattern, '', content, flags=re.DOTALL | re.IGNORECASE)
            
        return content
    
    def process_content_for_extraction(self, html_content: str) -> str:
        """
        Process HTML content to prepare it for extraction.
        
        This method applies all cleaning and processing steps to make the
        content more suitable for data extraction.
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            Processed HTML ready for extraction
        """
        # Apply processing pipeline
        content = html_content
        
        # 1. Remove boilerplate
        content = self.remove_boilerplate(content)
        
        # 2. Clean HTML
        content = self.clean_html(content)
        
        # 3. Extract main content area if possible
        main_content = self.extract_main_content(content)
        if len(main_content) >= self.min_content_length:
            content = main_content
        
        return content
    
    def optimize_for_product_extraction(self, html_content: str) -> str:
        """
        Optimize HTML specifically for product data extraction.
        
        This method focuses on preserving product-specific elements like
        prices, specifications, etc. while removing noise.
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            HTML optimized for product data extraction
        """
        content = self.process_content_for_extraction(html_content)
        
        # Preserve product-specific elements
        # This ensures price, specs, etc. are not removed even if they're in divs
        # that might match boilerplate patterns
        product_elements = [
            r'<div[^>]*?class="[^"]*?(?:price|product[-_]price|specs|specification|product[-_]details|features)[^"]*?"[^>]*>.*?</div>',
            r'<span[^>]*?class="[^"]*?(?:price|product[-_]price)[^"]*?"[^>]*>.*?</span>',
            r'<table[^>]*?class="[^"]*?(?:specs|specification)[^"]*?"[^>]*>.*?</table>'
        ]
        
        # Extract product elements from original HTML
        preserved_elements = []
        for pattern in product_elements:
            matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
            preserved_elements.extend(matches)
        
        # If we found preserved elements, add them back to the processed content
        if preserved_elements:
            # Add a container to hold preserved elements
            preserved_html = '<div class="preserved-product-elements">' + \
                             ''.join(preserved_elements) + \
                             '</div>'
            
            # Add preserved elements at the end of the content
            content += preserved_html
        
        return content 