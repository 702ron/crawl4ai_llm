"""
Unit tests for the ContentProcessor class.
"""

import pytest
import re

from crawl4ai_llm.processing import ContentProcessor, DataProcessingError


class TestContentProcessor:
    """Test cases for the ContentProcessor class."""

    def setup_method(self):
        """Set up test data before each test."""
        # Create a processor instance with default settings
        self.processor = ContentProcessor()
        
        # Create some sample HTML content for testing
        self.basic_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Page</title>
            <script>
                console.log("This should be removed");
            </script>
            <style>
                body { font-family: Arial; }
            </style>
        </head>
        <body>
            <header>
                <nav>Navigation menu</nav>
            </header>
            <div id="content">
                <h1>Product Title</h1>
                <p>This is a product description with some details.</p>
                <div class="price">$99.99</div>
            </div>
            <footer>
                Copyright 2023
            </footer>
            <!-- This is a comment that should be removed -->
        </body>
        </html>
        """
        
        self.product_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Product Page</title>
        </head>
        <body>
            <header>Site Header</header>
            <nav>
                <ul>
                    <li>Home</li>
                    <li>Products</li>
                    <li>Contact</li>
                </ul>
            </nav>
            <main>
                <h1>iPhone 13 Pro Max</h1>
                <div class="product-details">
                    <p>Experience the latest iPhone with amazing camera system and powerful A15 Bionic chip.</p>
                    <div class="price">$1099.99</div>
                    <div class="specs">
                        <h3>Specifications</h3>
                        <ul>
                            <li>6.7-inch Super Retina XDR display</li>
                            <li>A15 Bionic chip</li>
                            <li>Pro camera system</li>
                            <li>Up to 1TB storage</li>
                        </ul>
                    </div>
                </div>
            </main>
            <footer>
                <div class="copyright">Copyright 2023</div>
                <div class="links">
                    <a href="#">Privacy Policy</a>
                    <a href="#">Terms of Service</a>
                </div>
            </footer>
        </body>
        </html>
        """

    def test_initialization(self):
        """Test that ContentProcessor initializes with correct default values."""
        processor = ContentProcessor()
        assert processor.remove_scripts is True
        assert processor.remove_styles is True
        assert processor.remove_comments is True
        assert processor.clean_whitespace is True
        assert processor.min_content_length == 50
        
        # Test custom initialization
        custom_processor = ContentProcessor(
            remove_scripts=False,
            remove_styles=False,
            clean_whitespace=False,
            min_content_length=100
        )
        assert custom_processor.remove_scripts is False
        assert custom_processor.remove_styles is False
        assert custom_processor.clean_whitespace is False
        assert custom_processor.min_content_length == 100

    def test_clean_html_removes_scripts(self):
        """Test that script tags are removed from HTML."""
        # Process with script removal enabled
        cleaned_html = self.processor.clean_html(self.basic_html)
        assert "<script>" not in cleaned_html
        assert "console.log" not in cleaned_html
        
        # Process with script removal disabled
        processor = ContentProcessor(remove_scripts=False)
        preserved_html = processor.clean_html(self.basic_html)
        assert "console.log" in preserved_html

    def test_clean_html_removes_styles(self):
        """Test that style tags are removed from HTML."""
        # Process with style removal enabled
        cleaned_html = self.processor.clean_html(self.basic_html)
        assert "<style>" not in cleaned_html
        assert "font-family" not in cleaned_html
        
        # Process with style removal disabled
        processor = ContentProcessor(remove_styles=False)
        preserved_html = processor.clean_html(self.basic_html)
        assert "font-family" in preserved_html

    def test_clean_html_removes_comments(self):
        """Test that HTML comments are removed."""
        # Process with comment removal enabled
        cleaned_html = self.processor.clean_html(self.basic_html)
        assert "<!-- This is a comment" not in cleaned_html
        
        # Process with comment removal disabled
        processor = ContentProcessor(remove_comments=False)
        preserved_html = processor.clean_html(self.basic_html)
        assert "<!-- This is a comment" in preserved_html

    def test_clean_html_normalizes_whitespace(self):
        """Test that whitespace is normalized in cleaned HTML."""
        # Create HTML with extra whitespace
        html_with_whitespace = """
        <div>
            <p>   This    has    extra    spaces    </p>
            
            <p>This has extra lines</p>
        </div>
        """
        
        # Process with whitespace cleaning enabled
        cleaned_html = self.processor.clean_html(html_with_whitespace)
        assert "   This    has    extra    spaces    " not in cleaned_html
        assert re.search(r"This\s+has\s+extra\s+spaces", cleaned_html)
        
        # Process with whitespace cleaning disabled
        processor = ContentProcessor(clean_whitespace=False)
        preserved_html = processor.clean_html(html_with_whitespace)
        assert "   This    has    extra    spaces    " in preserved_html

    def test_clean_html_with_empty_content(self):
        """Test that an exception is raised for empty content."""
        with pytest.raises(DataProcessingError):
            self.processor.clean_html("")
            
        with pytest.raises(DataProcessingError):
            self.processor.clean_html(None)

    def test_extract_main_content(self):
        """Test extraction of main content from a page."""
        main_content = self.processor.extract_main_content(self.product_html)
        
        # Main content should include the product details
        assert "iPhone 13 Pro Max" in main_content
        assert "Experience the latest iPhone" in main_content
        assert "Specifications" in main_content
        
        # Main content should not include header and footer
        assert "Site Header" not in main_content
        assert "Copyright 2023" not in main_content

    def test_extract_text_blocks(self):
        """Test extraction of text blocks from HTML."""
        text_blocks = self.processor.extract_text_blocks(self.product_html)
        
        # Check that meaningful text blocks are extracted
        assert any("Experience the latest iPhone" in block for block in text_blocks)
        assert any("6.7-inch Super Retina XDR display" in block for block in text_blocks)
        
        # Very short blocks should be excluded based on min_content_length
        short_blocks = [block for block in text_blocks if len(block) < self.processor.min_content_length]
        assert len(short_blocks) == 0
        
        # Test with a custom min_content_length
        processor = ContentProcessor(min_content_length=10)
        text_blocks = processor.extract_text_blocks(self.product_html)
        assert any("iPhone 13 Pro Max" in block for block in text_blocks)

    def test_remove_boilerplate(self):
        """Test removal of boilerplate content."""
        cleaned_html = self.processor.remove_boilerplate(self.product_html)
        
        # Boilerplate content should be removed
        assert "<header>Site Header</header>" not in cleaned_html
        assert "<nav>" not in cleaned_html
        assert "<footer>" not in cleaned_html
        
        # Product content should be preserved
        assert "iPhone 13 Pro Max" in cleaned_html
        assert "Experience the latest iPhone" in cleaned_html
        assert "$1099.99" in cleaned_html

    def test_process_content_for_extraction(self):
        """Test the full content processing pipeline for extraction."""
        processed_content = self.processor.process_content_for_extraction(self.product_html)
        
        # Scripts, styles, comments should be removed
        assert "<script>" not in processed_content
        assert "<style>" not in processed_content
        assert "<!--" not in processed_content
        
        # Boilerplate content should be removed
        assert "<header>Site Header</header>" not in processed_content
        assert "<footer>" not in processed_content
        
        # Product content should be preserved
        assert "iPhone 13 Pro Max" in processed_content
        assert "Experience the latest iPhone" in processed_content
        assert "$1099.99" in processed_content

    def test_optimize_for_product_extraction(self):
        """Test optimization specifically for product data extraction."""
        # Create HTML with product specific elements
        product_page = """
        <!DOCTYPE html>
        <html>
        <head><title>Product Page</title></head>
        <body>
            <header>Site Header</header>
            <div class="content">
                <h1>Test Product</h1>
                <p>Product description</p>
            </div>
            <div class="sidebar">
                <div class="price">$59.99</div>
                <div class="specifications">
                    <ul>
                        <li>Spec 1: Value 1</li>
                        <li>Spec 2: Value 2</li>
                    </ul>
                </div>
            </div>
            <footer>Footer content</footer>
        </body>
        </html>
        """
        
        optimized = self.processor.optimize_for_product_extraction(product_page)
        
        # Boilerplate should be removed
        assert "<header>Site Header</header>" not in optimized
        assert "<footer>Footer content</footer>" not in optimized
        
        # Product content should be preserved
        assert "Test Product" in optimized
        assert "Product description" in optimized
        
        # Price should be preserved (important for product data)
        assert "$59.99" in optimized
        
        # Product specifications should be preserved
        assert "Spec 1: Value 1" in optimized
        assert "Spec 2: Value 2" in optimized 