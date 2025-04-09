"""
Content filtering strategies for crawling.

This module provides content filtering strategies for crawling web pages,
wrapping around the ContentFilter classes from the crawl4ai package.
"""

from typing import List, Optional, Union, Type, Dict, Any, Literal
import re
from bs4 import BeautifulSoup

from crawl4ai.content_filter_strategy import (
    RelevantContentFilter,
    BM25ContentFilter,
    PruningContentFilter,
    LLMContentFilter,
)

from ..config import LLMConfig


class CSSContentFilter:
    """Filter content using CSS selectors."""
    
    def __init__(self, selector: str, extract_text: bool = True):
        """
        Initialize a CSS selector filter.
        
        Args:
            selector: CSS selector to match elements.
            extract_text: Whether to extract text only (True) or HTML (False).
        """
        self.selector = selector
        self.extract_text = extract_text
        
    def filter_content(self, html: str) -> List[str]:
        """
        Filter content from HTML using CSS selectors.
        
        Args:
            html: HTML content to filter.
            
        Returns:
            List of filtered content chunks.
        """
        soup = BeautifulSoup(html, 'html.parser')
        elements = soup.select(self.selector)
        
        if self.extract_text:
            return [elem.get_text(strip=True) for elem in elements]
        else:
            return [str(elem) for elem in elements]


class XPathContentFilter:
    """Filter content using XPath expressions."""
    
    def __init__(self, selector: str, extract_text: bool = True):
        """
        Initialize an XPath filter.
        
        Args:
            selector: XPath expression to match elements.
            extract_text: Whether to extract text only (True) or HTML (False).
        """
        self.selector = selector
        self.extract_text = extract_text
        
    def filter_content(self, html: str) -> List[str]:
        """
        Filter content from HTML using XPath expressions.
        
        Args:
            html: HTML content to filter.
            
        Returns:
            List of filtered content chunks.
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # BeautifulSoup doesn't support XPath directly, use lxml if available
        try:
            from lxml import etree
            from lxml.html import fromstring
            
            # Parse the HTML with lxml
            tree = fromstring(html)
            
            # Find elements matching the XPath
            elements = tree.xpath(self.selector)
            
            results = []
            for elem in elements:
                if self.extract_text:
                    # Extract text based on element type
                    if isinstance(elem, str):
                        # Text node or attribute value
                        results.append(elem.strip())
                    elif hasattr(elem, 'text_content'):
                        # Element node with text
                        results.append(elem.text_content().strip())
                    else:
                        # Other (convert to string)
                        results.append(str(elem).strip())
                else:
                    # Return HTML representation
                    if isinstance(elem, str):
                        # Text node or attribute value
                        results.append(elem)
                    elif hasattr(elem, 'tag'):
                        # Element node
                        results.append(etree.tostring(elem, encoding='unicode'))
                    else:
                        # Other
                        results.append(str(elem))
            
            return results
        except ImportError:
            # Fallback if lxml is not available - note that this is limited
            # and will only work for very simple XPath expressions
            # This is a basic implementation for simple cases only
            if self.selector.startswith('//'):
                tag = self.selector.split('//')[1].split('[')[0]
                attrs = {}
                
                # Handle simple attribute selector like //div[@class='product']
                if '[' in self.selector and ']' in self.selector:
                    attr_part = self.selector.split('[')[1].split(']')[0]
                    if '@' in attr_part and '=' in attr_part:
                        attr_name = attr_part.split('@')[1].split('=')[0]
                        attr_value = attr_part.split('=')[1].strip("'\"")
                        attrs[attr_name] = attr_value
                
                elements = soup.find_all(tag, attrs)
                
                if self.extract_text:
                    return [elem.get_text(strip=True) for elem in elements]
                else:
                    return [str(elem) for elem in elements]
            
            return []


class RegexContentFilter:
    """Filter content using regular expressions."""
    
    def __init__(self, pattern: str, replacement: Optional[str] = None):
        """
        Initialize a regex filter.
        
        Args:
            pattern: Regular expression pattern to match.
            replacement: Optional replacement string for matches.
        """
        self.pattern = pattern
        self.replacement = replacement
        self.compiled_pattern = re.compile(pattern)
        
    def filter_content(self, html: str) -> List[str]:
        """
        Filter content from HTML using regex pattern.
        
        Args:
            html: HTML content to filter.
            
        Returns:
            List of filtered content chunks.
        """
        if self.replacement is not None:
            # Return the content with replacements
            return [re.sub(self.compiled_pattern, self.replacement, html)]
        else:
            # Return the matched groups
            matches = self.compiled_pattern.findall(html)
            
            if not matches:
                return []
                
            # Handle different match types
            if isinstance(matches[0], tuple):
                # Multiple capture groups
                return [" ".join(match) for match in matches]
            else:
                # Single items
                return matches


class ContentFilter:
    """
    Wrapper around crawl4ai ContentFilter classes.

    This class provides a unified interface for content filtering strategies
    from the crawl4ai package, with simplified configuration.
    """

    def __init__(
        self,
        filter_type: str = "bm25",
        query: Optional[str] = None,
        llm_config: Optional[LLMConfig] = None,
        instruction: Optional[str] = None,
        threshold: float = 1.0,
        selector: Optional[str] = None,
        extract_text: Optional[bool] = None,
        pattern: Optional[str] = None,
        replacement: Optional[str] = None,
    ):
        """
        Initialize a content filter.

        Args:
            filter_type: Type of filter to use. Options: "bm25", "pruning", "llm", "css", "xpath", "regex".
            query: Optional query to use for filtering content (for "bm25" and "pruning").
            llm_config: LLM configuration for LLM-based filtering.
            instruction: Custom instruction for LLM-based filtering.
            threshold: Threshold value for filtering (applies to BM25 and Pruning).
            selector: CSS selector or XPath expression for "css" and "xpath" filter types.
            extract_text: Whether to extract text only (True) or HTML (False) for "css" and "xpath" filters.
            pattern: Regular expression pattern for "regex" filter type.
            replacement: Optional replacement string for regex matches.
        
        Raises:
            ValueError: If filter_type is "llm" but llm_config is not provided.
            ValueError: If filter_type is not one of the supported types.
            ValueError: If required parameters for a specific filter type are missing.
        """
        self.filter_type = filter_type
        self.query = query
        self.llm_config = llm_config
        self.instruction = instruction
        self.threshold = threshold
        self.selector = selector
        self.extract_text = extract_text
        self.pattern = pattern
        self.replacement = replacement
        
        # Create the underlying filter
        self._filter = self._create_filter()
    
    def _create_filter(self) -> Union[RelevantContentFilter, CSSContentFilter, XPathContentFilter, RegexContentFilter]:
        """
        Create the appropriate filter based on configuration.
        
        Returns:
            An instance of a ContentFilter from crawl4ai package or a custom filter.
            
        Raises:
            ValueError: If filter_type is "llm" but llm_config is not provided.
            ValueError: If filter_type is not one of the supported types.
            ValueError: If required parameters for a specific filter type are missing.
        """
        if self.filter_type == "bm25":
            return BM25ContentFilter(
                user_query=self.query,
                bm25_threshold=self.threshold
            )
        elif self.filter_type == "pruning":
            return PruningContentFilter(
                user_query=self.query,
                threshold=self.threshold
            )
        elif self.filter_type == "llm":
            if not self.llm_config:
                raise ValueError("LLMConfig is required for LLM-based content filtering")
            
            return LLMContentFilter(
                llm_config=self.llm_config,
                instruction=self.instruction
            )
        elif self.filter_type == "css":
            if not self.selector:
                raise ValueError("selector is required for css filter")
            
            return CSSContentFilter(
                selector=self.selector,
                extract_text=self.extract_text if self.extract_text is not None else True
            )
        elif self.filter_type == "xpath":
            if not self.selector:
                raise ValueError("selector is required for xpath filter")
            
            return XPathContentFilter(
                selector=self.selector,
                extract_text=self.extract_text if self.extract_text is not None else True
            )
        elif self.filter_type == "regex":
            if not self.pattern:
                raise ValueError("pattern is required for regex filter")
            
            return RegexContentFilter(
                pattern=self.pattern,
                replacement=self.replacement
            )
        else:
            raise ValueError(
                f"Invalid filter_type: {self.filter_type}. "
                "Supported types: bm25, pruning, llm, css, xpath, regex"
            )
    
    def filter_content(self, html: str) -> List[str]:
        """
        Filter content from HTML.
        
        Args:
            html: HTML content to filter.
            
        Returns:
            List of filtered content chunks.
        """
        return self._filter.filter_content(html)
        
    def __str__(self) -> str:
        """
        String representation of the ContentFilter.
        
        Returns:
            String representation with filter type and main parameters.
        """
        if self.filter_type in ["css", "xpath"]:
            return f"ContentFilter(type={self.filter_type}, selector={self.selector})"
        elif self.filter_type == "regex":
            return f"ContentFilter(type={self.filter_type}, pattern={self.pattern})"
        elif self.filter_type in ["bm25", "pruning"]:
            return f"ContentFilter(type={self.filter_type}, query={self.query})"
        elif self.filter_type == "llm":
            return f"ContentFilter(type={self.filter_type}, instruction={self.instruction})"
        else:
            return f"ContentFilter(type={self.filter_type})"


class ContentFilterChain:
    """
    Chain multiple content filters together in a specific strategy.
    
    This class provides several strategies for combining multiple content filters:
    - ALL: Content must pass through all filters (intersection of results)
    - ANY: Content passes if it meets any filter's criteria (union of results)
    - SEQUENCE: Filters are applied in sequence, with each filter processing the output of the previous one
    """
    
    def __init__(
        self,
        filters: List[ContentFilter],
        strategy: Literal["ALL", "ANY", "SEQUENCE"] = "SEQUENCE",
        name: Optional[str] = None
    ):
        """
        Initialize a content filter chain.
        
        Args:
            filters: List of ContentFilter instances to chain together.
            strategy: How to combine filter results:
                - ALL: Intersection of all filter results
                - ANY: Union of all filter results
                - SEQUENCE: Apply filters in sequence (output of one becomes input to the next)
            name: Optional name for this filter chain for identification.
            
        Raises:
            ValueError: If filters list is empty or strategy is invalid.
        """
        if not filters:
            raise ValueError("ContentFilterChain requires at least one filter")
            
        if strategy not in ["ALL", "ANY", "SEQUENCE"]:
            raise ValueError("Strategy must be one of: ALL, ANY, SEQUENCE")
            
        self.filters = filters
        self.strategy = strategy
        self.name = name or f"ContentFilterChain({strategy})"
        
    def filter_content(self, html: str) -> List[str]:
        """
        Apply the filter chain to HTML content.
        
        Args:
            html: HTML content to filter.
            
        Returns:
            List of filtered content chunks.
        """
        if not self.filters:
            return [html]
            
        if self.strategy == "SEQUENCE":
            # Apply filters in sequence
            current_content = [html]
            for content_filter in self.filters:
                # Apply the current filter to each chunk from the previous step
                next_content = []
                for chunk in current_content:
                    filtered_chunks = content_filter.filter_content(chunk)
                    next_content.extend(filtered_chunks)
                current_content = next_content
                
                # If we get no results at any point, stop processing
                if not current_content:
                    break
                    
            return current_content
            
        elif self.strategy == "ALL":
            # Content must pass all filters (intersection)
            # First, get all results from each filter
            all_filtered_content = []
            for content_filter in self.filters:
                filtered_content = content_filter.filter_content(html)
                all_filtered_content.append(set(filtered_content))
                
            # Find the intersection of all results
            if not all_filtered_content:
                return []
                
            intersection = all_filtered_content[0]
            for content_set in all_filtered_content[1:]:
                intersection &= content_set
                
            return list(intersection)
            
        elif self.strategy == "ANY":
            # Content passes if it meets any filter's criteria (union)
            all_results = set()
            for content_filter in self.filters:
                filtered_content = content_filter.filter_content(html)
                all_results.update(filtered_content)
                
            return list(all_results)
    
        # Should never get here due to validation in __init__
        return []
        
    def __str__(self) -> str:
        """
        String representation of the ContentFilterChain.
        
        Returns:
            String representation with strategy and filters.
        """
        filter_strs = [str(f) for f in self.filters]
        return f"ContentFilterChain(strategy={self.strategy}, filters=[{', '.join(filter_strs)}])" 