"""
Schema analyzer for product extraction.

This module provides functionality to analyze HTML content and generate
extraction schemas by detecting patterns and common element structures.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from bs4 import BeautifulSoup, Tag

from .schema_validator import SchemaValidator, COMMON_PRODUCT_FIELDS, REQUIRED_FIELDS

logger = logging.getLogger(__name__)


@dataclass
class ElementScore:
    """Score for an HTML element as a potential field selector."""
    selector: str
    element: Tag
    score: float
    field_type: str
    attribute: str = "text"


class SchemaAnalyzer:
    """
    Analyzes HTML content to detect patterns and infer extraction schemas.
    """
    
    def __init__(self, validator: Optional[SchemaValidator] = None):
        """
        Initialize a schema analyzer.
        
        Args:
            validator: Optional schema validator to validate generated schemas.
        """
        self.validator = validator or SchemaValidator()
        
    def analyze_html(self, html: str, url: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze HTML content and generate an extraction schema.
        
        Args:
            html: The HTML content to analyze.
            url: Optional URL of the page, used for domain hints.
            
        Returns:
            A generated extraction schema.
        """
        if not html:
            logger.warning("Empty HTML content provided for analysis")
            return self._create_empty_schema()
            
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract domain hints from URL if available
            domain_hints = self._extract_domain_hints(url) if url else {}
            
            # Generate field candidates
            field_candidates = self._generate_field_candidates(soup, domain_hints)
            
            # Create schema from candidates
            schema = self._create_schema_from_candidates(field_candidates)
            
            # Validate and correct the schema
            if self.validator:
                schema = self.validator.correct_schema(schema)
                
            return schema
            
        except Exception as e:
            logger.error(f"Error analyzing HTML content: {str(e)}")
            return self._create_empty_schema()
    
    def _extract_domain_hints(self, url: str) -> Dict[str, Any]:
        """
        Extract domain hints from URL to guide schema generation.
        
        Args:
            url: The URL to analyze.
            
        Returns:
            Dictionary of domain hints.
        """
        hints = {}
        
        if not url:
            return hints
            
        # Extract domain
        domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url.lower())
        if not domain_match:
            return hints
            
        domain = domain_match.group(1)
        
        # Identify e-commerce domain type
        if any(kw in domain for kw in ['amazon', 'ebay', 'walmart', 'target', 'bestbuy']):
            hints['domain_type'] = 'major_retailer'
        elif any(kw in domain for kw in ['electronics', 'tech', 'gadget']):
            hints['domain_type'] = 'electronics'
        elif any(kw in domain for kw in ['apparel', 'clothing', 'fashion', 'wear']):
            hints['domain_type'] = 'fashion'
        elif any(kw in domain for kw in ['food', 'grocery', 'fresh']):
            hints['domain_type'] = 'grocery'
        elif any(kw in domain for kw in ['furniture', 'home', 'decor']):
            hints['domain_type'] = 'furniture'
        else:
            hints['domain_type'] = 'general'
            
        # Store domain for reference
        hints['domain'] = domain
        
        return hints
    
    def _generate_field_candidates(
        self, 
        soup: BeautifulSoup, 
        domain_hints: Dict[str, Any]
    ) -> Dict[str, List[ElementScore]]:
        """
        Generate candidate elements for each field type.
        
        Args:
            soup: The parsed HTML content.
            domain_hints: Hints about the domain type.
            
        Returns:
            Dictionary mapping field names to candidate elements with scores.
        """
        candidates = {}
        
        # Process each common field type
        for field_name in COMMON_PRODUCT_FIELDS:
            field_candidates = self._find_candidates_for_field(field_name, soup, domain_hints)
            if field_candidates:
                candidates[field_name] = field_candidates
                
        return candidates
    
    def _find_candidates_for_field(
        self, 
        field_name: str, 
        soup: BeautifulSoup, 
        domain_hints: Dict[str, Any]
    ) -> List[ElementScore]:
        """
        Find candidate elements for a specific field.
        
        Args:
            field_name: The field to find candidates for.
            soup: The parsed HTML content.
            domain_hints: Hints about the domain type.
            
        Returns:
            List of candidate elements with scores.
        """
        candidates = []
        
        # Get common patterns for this field
        patterns = self._get_field_patterns(field_name, domain_hints)
        
        # Find elements matching predefined selectors
        for selector_info in patterns.get('selectors', []):
            selector = selector_info['selector']
            attribute = selector_info.get('attribute', 'text')
            
            try:
                elements = soup.select(selector)
                for element in elements:
                    # Skip empty elements
                    if attribute == 'text':
                        content = element.get_text(strip=True)
                    else:
                        content = element.get(attribute, '')
                        
                    if not content:
                        continue
                        
                    # Calculate score based on position, size, and match to expected format
                    score = self._calculate_element_score(
                        element, 
                        field_name, 
                        attribute, 
                        content, 
                        selector_info.get('base_score', 0.5)
                    )
                    
                    # Create selector path
                    selector_path = self._create_selector_path(element)
                    candidates.append(ElementScore(
                        selector=selector_path,
                        element=element,
                        score=score,
                        field_type=field_name,
                        attribute=attribute
                    ))
            except Exception as e:
                logger.warning(f"Error finding elements for selector {selector}: {str(e)}")
        
        # Find elements using heuristic search
        heuristic_candidates = self._find_candidates_heuristically(soup, field_name, patterns)
        candidates.extend(heuristic_candidates)
        
        # Sort by score (descending)
        return sorted(candidates, key=lambda x: x.score, reverse=True)
    
    def _get_field_patterns(self, field_name: str, domain_hints: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get patterns for detecting a specific field type.
        
        Args:
            field_name: The field to get patterns for.
            domain_hints: Hints about the domain type.
            
        Returns:
            Dictionary of patterns for the field.
        """
        # Common patterns for all fields
        common_patterns = {
            "title": {
                "selectors": [
                    {"selector": "h1", "attribute": "text", "base_score": 0.8},
                    {"selector": ".product-title", "attribute": "text", "base_score": 0.7},
                    {"selector": ".product-name", "attribute": "text", "base_score": 0.7},
                    {"selector": "[itemprop='name']", "attribute": "text", "base_score": 0.9},
                    {"selector": "[data-testid='product-title']", "attribute": "text", "base_score": 0.9},
                    {"selector": "title", "attribute": "text", "base_score": 0.5}
                ],
                "keywords": ["title", "name", "product"],
                "regex": None,
                "expected_format": "text",
                "common_classes": ["title", "product-title", "product-name", "name"]
            },
            "price": {
                "selectors": [
                    {"selector": ".price", "attribute": "text", "base_score": 0.7},
                    {"selector": ".product-price", "attribute": "text", "base_score": 0.7},
                    {"selector": "[itemprop='price']", "attribute": "content", "base_score": 0.9},
                    {"selector": "[data-testid='price']", "attribute": "text", "base_score": 0.9},
                    {"selector": "[data-price]", "attribute": "data-price", "base_score": 0.8}
                ],
                "keywords": ["price", "cost", "$", "€", "£"],
                "regex": r'(\$|€|£|\d+[,.]\d{2})',
                "expected_format": "price",
                "common_classes": ["price", "product-price", "current-price", "sale-price"]
            },
            "description": {
                "selectors": [
                    {"selector": ".description", "attribute": "text", "base_score": 0.7},
                    {"selector": ".product-description", "attribute": "text", "base_score": 0.7},
                    {"selector": "[itemprop='description']", "attribute": "text", "base_score": 0.9},
                    {"selector": "#description", "attribute": "text", "base_score": 0.7},
                    {"selector": "#product-description", "attribute": "text", "base_score": 0.7}
                ],
                "keywords": ["description", "about", "details", "overview"],
                "regex": None,
                "expected_format": "long_text",
                "common_classes": ["description", "product-description", "details", "overview"]
            },
            "brand": {
                "selectors": [
                    {"selector": ".brand", "attribute": "text", "base_score": 0.7},
                    {"selector": "[itemprop='brand']", "attribute": "text", "base_score": 0.9},
                    {"selector": "[data-testid='brand']", "attribute": "text", "base_score": 0.9}
                ],
                "keywords": ["brand", "manufacturer", "made by"],
                "regex": None,
                "expected_format": "text",
                "common_classes": ["brand", "manufacturer", "vendor"]
            },
            "images": {
                "selectors": [
                    {"selector": ".product-image img", "attribute": "src", "base_score": 0.7},
                    {"selector": ".gallery img", "attribute": "src", "base_score": 0.6},
                    {"selector": "[itemprop='image']", "attribute": "src", "base_score": 0.9},
                    {"selector": "[itemprop='image']", "attribute": "content", "base_score": 0.9},
                    {"selector": ".product-gallery img", "attribute": "src", "base_score": 0.7},
                    {"selector": ".carousel img", "attribute": "src", "base_score": 0.6}
                ],
                "keywords": ["image", "photo", "picture", "gallery"],
                "regex": r'(\.jpg|\.jpeg|\.png|\.gif|\.webp)',
                "expected_format": "url",
                "common_classes": ["product-image", "gallery", "carousel", "product-gallery"]
            },
            "sku": {
                "selectors": [
                    {"selector": "[itemprop='sku']", "attribute": "text", "base_score": 0.9},
                    {"selector": "[data-testid='sku']", "attribute": "text", "base_score": 0.9},
                    {"selector": ".sku", "attribute": "text", "base_score": 0.7},
                    {"selector": ".product-sku", "attribute": "text", "base_score": 0.7}
                ],
                "keywords": ["sku", "item number", "product number", "model"],
                "regex": r'(SKU|Model|Item)[\s:#]*([A-Z0-9\-]+)',
                "expected_format": "alphanumeric",
                "common_classes": ["sku", "product-sku", "item-number", "model-number"]
            },
            "availability": {
                "selectors": [
                    {"selector": "[itemprop='availability']", "attribute": "content", "base_score": 0.9},
                    {"selector": ".availability", "attribute": "text", "base_score": 0.7},
                    {"selector": ".stock", "attribute": "text", "base_score": 0.7},
                    {"selector": "[data-testid='availability']", "attribute": "text", "base_score": 0.9}
                ],
                "keywords": ["in stock", "out of stock", "available", "unavailable", "availability"],
                "regex": r'(in stock|out of stock|available|unavailable)',
                "expected_format": "text",
                "common_classes": ["availability", "stock", "in-stock", "out-of-stock"]
            }
        }
        
        # Domain-specific pattern overrides
        domain_type = domain_hints.get('domain_type', 'general')
        domain_patterns = {}
        
        if domain_type == 'electronics':
            domain_patterns = {
                "specifications": {
                    "selectors": [
                        {"selector": ".specifications", "attribute": "text", "base_score": 0.7},
                        {"selector": ".specs", "attribute": "text", "base_score": 0.7},
                        {"selector": ".tech-specs", "attribute": "text", "base_score": 0.7},
                        {"selector": "table.specs", "attribute": "text", "base_score": 0.6}
                    ],
                    "keywords": ["specs", "specifications", "technical details"],
                    "regex": None,
                    "expected_format": "long_text",
                    "common_classes": ["specifications", "specs", "tech-specs"]
                }
            }
        elif domain_type == 'fashion':
            domain_patterns = {
                "sizes": {
                    "selectors": [
                        {"selector": ".sizes", "attribute": "text", "base_score": 0.7},
                        {"selector": ".size-options", "attribute": "text", "base_score": 0.7},
                        {"selector": "[data-testid='size-options']", "attribute": "text", "base_score": 0.9}
                    ],
                    "keywords": ["size", "sizes", "available sizes"],
                    "regex": None,
                    "expected_format": "text",
                    "common_classes": ["sizes", "size-options", "size-selector"]
                },
                "colors": {
                    "selectors": [
                        {"selector": ".colors", "attribute": "text", "base_score": 0.7},
                        {"selector": ".color-options", "attribute": "text", "base_score": 0.7},
                        {"selector": "[data-testid='color-options']", "attribute": "text", "base_score": 0.9}
                    ],
                    "keywords": ["color", "colors", "available colors"],
                    "regex": None,
                    "expected_format": "text",
                    "common_classes": ["colors", "color-options", "color-selector"]
                }
            }
        
        # Combine common and domain-specific patterns
        return domain_patterns.get(field_name, common_patterns.get(field_name, {
            "selectors": [],
            "keywords": [],
            "regex": None,
            "expected_format": "text",
            "common_classes": []
        }))
    
    def _find_candidates_heuristically(
        self, 
        soup: BeautifulSoup, 
        field_name: str, 
        patterns: Dict[str, Any]
    ) -> List[ElementScore]:
        """
        Find candidate elements using heuristic search.
        
        Args:
            soup: The parsed HTML content.
            field_name: The field to find candidates for.
            patterns: Patterns for the field.
            
        Returns:
            List of candidate elements with scores.
        """
        candidates = []
        
        # Get keywords, regex and common class patterns for this field
        keywords = patterns.get('keywords', [])
        regex_pattern = patterns.get('regex')
        common_classes = patterns.get('common_classes', [])
        
        # Search for elements containing keywords
        for keyword in keywords:
            elements = self._find_elements_with_text(soup, keyword)
            for element in elements:
                # Calculate score
                content = element.get_text(strip=True)
                score = self._calculate_element_score(element, field_name, 'text', content, 0.3)
                
                # Create selector path
                selector_path = self._create_selector_path(element)
                candidates.append(ElementScore(
                    selector=selector_path,
                    element=element,
                    score=score,
                    field_type=field_name,
                    attribute='text'
                ))
        
        # Search for elements matching regex pattern
        if regex_pattern:
            elements = self._find_elements_with_regex(soup, regex_pattern)
            for element in elements:
                # Calculate score
                content = element.get_text(strip=True)
                score = self._calculate_element_score(element, field_name, 'text', content, 0.4)
                
                # Create selector path
                selector_path = self._create_selector_path(element)
                candidates.append(ElementScore(
                    selector=selector_path,
                    element=element,
                    score=score,
                    field_type=field_name,
                    attribute='text'
                ))
        
        # Search for elements with common classes
        for class_name in common_classes:
            elements = soup.find_all(class_=re.compile(class_name, re.IGNORECASE))
            for element in elements:
                # Calculate score
                content = element.get_text(strip=True)
                if not content:
                    continue
                    
                score = self._calculate_element_score(element, field_name, 'text', content, 0.5)
                
                # Create selector path
                selector_path = self._create_selector_path(element)
                candidates.append(ElementScore(
                    selector=selector_path,
                    element=element,
                    score=score,
                    field_type=field_name,
                    attribute='text'
                ))
                
        # Special handling for images
        if field_name == 'images':
            # Find all img elements in product context
            product_containers = soup.find_all(['div', 'section'], class_=re.compile(r'product|item|gallery', re.IGNORECASE))
            if not product_containers:
                product_containers = [soup]
                
            for container in product_containers:
                images = container.find_all('img')
                for img in images:
                    src = img.get('src', '')
                    if not src or src.endswith(('.gif', '.svg')) or 'icon' in src.lower():
                        continue
                        
                    # Exclude small icons
                    width = img.get('width', '0')
                    height = img.get('height', '0')
                    if width.isdigit() and height.isdigit():
                        if int(width) < 100 or int(height) < 100:
                            continue
                    
                    score = 0.4
                    if 'product' in img.get('class', [''])[0].lower():
                        score += 0.3
                    if 'main' in img.get('class', [''])[0].lower():
                        score += 0.2
                    
                    # Create selector path
                    selector_path = self._create_selector_path(img)
                    candidates.append(ElementScore(
                        selector=selector_path,
                        element=img,
                        score=score,
                        field_type='images',
                        attribute='src'
                    ))
        
        return candidates
    
    def _find_elements_with_text(self, soup: BeautifulSoup, text: str) -> List[Tag]:
        """
        Find elements containing specific text.
        
        Args:
            soup: The parsed HTML content.
            text: The text to search for.
            
        Returns:
            List of matching elements.
        """
        results = []
        text_pattern = re.compile(text, re.IGNORECASE)
        
        for element in soup.find_all(text=text_pattern):
            parent = element.parent
            if parent and parent.name not in ['script', 'style']:
                results.append(parent)
                
        return results
    
    def _find_elements_with_regex(self, soup: BeautifulSoup, pattern: str) -> List[Tag]:
        """
        Find elements with text matching a regex pattern.
        
        Args:
            soup: The parsed HTML content.
            pattern: The regex pattern to match.
            
        Returns:
            List of matching elements.
        """
        results = []
        regex = re.compile(pattern, re.IGNORECASE)
        
        for element in soup.find_all(text=regex):
            parent = element.parent
            if parent and parent.name not in ['script', 'style']:
                results.append(parent)
                
        return results
    
    def _calculate_element_score(
        self, 
        element: Tag, 
        field_name: str, 
        attribute: str, 
        content: str, 
        base_score: float
    ) -> float:
        """
        Calculate a score for an element as a candidate for a field.
        
        Args:
            element: The HTML element.
            field_name: The field type.
            attribute: The attribute to extract.
            content: The extracted content.
            base_score: The base score for this element.
            
        Returns:
            A score between 0 and 1.
        """
        score = base_score
        
        # Adjust score based on element position
        if element.name == 'h1':
            score += 0.2
        elif element.name in ['h2', 'h3']:
            score += 0.1
            
        # Adjust score based on element visibility
        if element.get('hidden') is not None or element.get('style') == 'display:none':
            score -= 0.5
            
        # Adjust score based on ID and class attributes
        element_id = element.get('id', '').lower()
        element_classes = ' '.join(element.get('class', [])).lower()
        
        if field_name.lower() in element_id:
            score += 0.2
        if any(variant in element_id for variant in self._get_field_variants(field_name)):
            score += 0.1
            
        if field_name.lower() in element_classes:
            score += 0.15
        if any(variant in element_classes for variant in self._get_field_variants(field_name)):
            score += 0.1
        
        # Special scoring for specific field types
        if field_name == 'price' and re.search(r'(\$|€|£|\d+[,.]\d{2})', content):
            score += 0.2
        elif field_name == 'title' and element.name == 'h1':
            score += 0.3
        elif field_name == 'description' and len(content) > 100:
            score += 0.1
        elif field_name == 'images' and attribute == 'src' and re.search(r'\.(jpg|jpeg|png|webp)', content):
            score += 0.2
            
        # Cap score to maximum of 1.0
        return min(1.0, max(0.0, score))
    
    def _create_selector_path(self, element: Tag) -> str:
        """
        Create a CSS selector path for an element.
        
        Args:
            element: The HTML element.
            
        Returns:
            A CSS selector string.
        """
        # Try to create a simple selector with ID if available
        if element.get('id'):
            return f"#{element['id']}"
            
        # Try to create a selector with a unique class
        element_classes = element.get('class', [])
        if element_classes:
            for cls in element_classes:
                # Skip very common classes
                if cls.lower() in ['row', 'col', 'container', 'wrapper', 'section']:
                    continue
                return f"{element.name}.{cls}"
        
        # For images with src, we can use attribute selector
        if element.name == 'img' and element.get('src'):
            src_parts = element['src'].split('/')
            if len(src_parts) > 1:
                filename = src_parts[-1].split('?')[0]  # Remove query string
                return f"img[src$='{filename}']"
                
        # Fall back to position-based selector (less robust)
        # Find a parent with ID or distinctive class
        parent = element.parent
        max_depth = 3
        depth = 0
        
        while parent and parent.name != 'body' and depth < max_depth:
            if parent.get('id'):
                # Calculate position among siblings
                siblings = list(parent.find_all(element.name, recursive=False))
                position = siblings.index(element) + 1 if element in siblings else 0
                
                if position > 0:
                    return f"#{parent['id']} > {element.name}:nth-of-type({position})"
                
            parent = parent.parent
            depth += 1
            
        # Last resort: basic tag name
        return element.name
    
    def _get_field_variants(self, field_name: str) -> List[str]:
        """
        Get common variants of a field name.
        
        Args:
            field_name: The field name.
            
        Returns:
            List of field name variants.
        """
        variants = []
        
        # Common variant mappings
        variant_map = {
            'title': ['name', 'product-name', 'product-title', 'product_name', 'product_title'],
            'price': ['product-price', 'current-price', 'sale-price', 'product_price', 'current_price'],
            'description': ['product-description', 'product_description', 'details', 'overview'],
            'brand': ['manufacturer', 'vendor', 'make'],
            'images': ['gallery', 'product-images', 'product_images', 'photo'],
            'sku': ['item-number', 'product-number', 'model-number', 'item_number'],
            'availability': ['stock', 'in-stock', 'inventory']
        }
        
        return variant_map.get(field_name.lower(), [])
    
    def _create_schema_from_candidates(
        self, 
        candidates: Dict[str, List[ElementScore]]
    ) -> Dict[str, Any]:
        """
        Create a schema from candidate elements.
        
        Args:
            candidates: Dictionary mapping field names to candidate elements.
            
        Returns:
            Generated extraction schema.
        """
        schema = {
            "name": "Generated Schema",
            "fields": []
        }
        
        # Track selected selectors to avoid duplicates
        selected_selectors = set()
        
        # Process each field type
        for field_name, field_candidates in candidates.items():
            # Skip if no candidates
            if not field_candidates:
                continue
                
            # Get top candidate for the field
            top_candidate = field_candidates[0]
            
            # Skip if selector already selected (avoid duplicates)
            if top_candidate.selector in selected_selectors:
                # Try to find an alternative
                alternative = None
                for candidate in field_candidates[1:]:
                    if candidate.selector not in selected_selectors and candidate.score > 0.4:
                        alternative = candidate
                        break
                        
                if not alternative:
                    continue
                    
                top_candidate = alternative
                
            # Add to selected selectors
            selected_selectors.add(top_candidate.selector)
            
            # Create field configuration
            field_config = {
                "name": field_name,
                "selector": top_candidate.selector,
                "attribute": top_candidate.attribute,
                "required": field_name in REQUIRED_FIELDS
            }
            
            # Handle special cases
            if field_name == 'images':
                field_config['array'] = True
                
            # Add alternatives if available
            alternatives = []
            for candidate in field_candidates[1:3]:  # Take up to 2 alternatives
                if candidate.selector not in selected_selectors and candidate.score > 0.3:
                    alternatives.append(candidate.selector)
                    
            if alternatives:
                field_config['alternative_selectors'] = alternatives
                
            # Add field to schema
            schema['fields'].append(field_config)
            
        # Ensure required fields are present (even with empty selectors)
        existing_fields = {f['name'] for f in schema['fields']}
        for field_name in REQUIRED_FIELDS:
            if field_name not in existing_fields:
                schema['fields'].append({
                    "name": field_name,
                    "selector": "",
                    "attribute": "text",
                    "required": True
                })
                
        return schema
    
    def _create_empty_schema(self) -> Dict[str, Any]:
        """
        Create an empty schema with required fields.
        
        Returns:
            Empty schema.
        """
        schema = {
            "name": "Empty Schema",
            "fields": []
        }
        
        # Add required fields with empty selectors
        for field_name in REQUIRED_FIELDS:
            schema['fields'].append({
                "name": field_name,
                "selector": "",
                "attribute": "text",
                "required": True
            })
            
        return schema


def generate_schema_from_html(html: str, url: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate an extraction schema from HTML content.
    
    Args:
        html: The HTML content to analyze.
        url: Optional URL of the page, used for domain hints.
        
    Returns:
        Generated extraction schema.
    """
    analyzer = SchemaAnalyzer()
    return analyzer.analyze_html(html, url) 