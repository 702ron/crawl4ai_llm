#!/usr/bin/env python
"""
Standalone test for the new content filter types.
"""

from crawl4ai_llm.crawler.content_filter import (ContentFilter,
                                                 CSSContentFilter,
                                                 RegexContentFilter,
                                                 XPathContentFilter)

# Test HTML content
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Product Page</title>
</head>
<body>
    <div id="product-container">
        <h1 id="product-title">Amazing Test Product</h1>
        <div class="product-price">$99.99</div>
        <div class="product-description">
            This is a fantastic product with many features.
        </div>
        <ul class="product-features">
            <li>Feature 1</li>
            <li>Feature 2</li>
            <li>Feature 3</li>
        </ul>
    </div>
</body>
</html>
"""


def test_css_filter():
    """Test CSS selector filter."""
    print("\n=== Testing CSS Filter ===")

    # Extract title with text only
    css_filter = CSSContentFilter(selector="#product-title", extract_text=True)
    results = css_filter.filter_content(HTML)
    print("Title (text only):", results)

    # Extract price element with HTML
    css_filter = CSSContentFilter(selector=".product-price", extract_text=False)
    results = css_filter.filter_content(HTML)
    print("Price (with HTML):", results)

    # Extract all features
    css_filter = CSSContentFilter(selector=".product-features li", extract_text=True)
    results = css_filter.filter_content(HTML)
    print("Features:", results)

    # Test with ContentFilter wrapper
    filter_wrapper = ContentFilter(
        filter_type="css", selector=".product-description", extract_text=True
    )
    results = filter_wrapper.filter_content(HTML)
    print("Description (via wrapper):", results)


def test_xpath_filter():
    """Test XPath filter."""
    print("\n=== Testing XPath Filter ===")

    # Extract title with text only
    xpath_filter = XPathContentFilter(
        selector="//h1[@id='product-title']", extract_text=True
    )
    results = xpath_filter.filter_content(HTML)
    print("Title (text only):", results)

    # Extract price with HTML
    xpath_filter = XPathContentFilter(
        selector="//div[@class='product-price']", extract_text=False
    )
    results = xpath_filter.filter_content(HTML)
    print("Price (with HTML):", results)

    # Extract all features
    xpath_filter = XPathContentFilter(
        selector="//ul[@class='product-features']/li", extract_text=True
    )
    results = xpath_filter.filter_content(HTML)
    print("Features:", results)

    # Test with ContentFilter wrapper
    filter_wrapper = ContentFilter(
        filter_type="xpath",
        selector="//div[@class='product-description']",
        extract_text=True,
    )
    results = filter_wrapper.filter_content(HTML)
    print("Description (via wrapper):", results)


def test_regex_filter():
    """Test regex filter."""
    print("\n=== Testing Regex Filter ===")

    # Extract price value
    regex_filter = RegexContentFilter(pattern=r"\$(\d+\.\d+)")
    results = regex_filter.filter_content(HTML)
    print("Price (extracted):", results)

    # Replace price with custom format
    regex_filter = RegexContentFilter(
        pattern=r"\$(\d+\.\d+)", replacement=r"Price: \1 USD"
    )
    results = regex_filter.filter_content(HTML)
    print("Modified HTML length:", len(results[0]))
    print(
        "Price section:",
        results[0][results[0].find("Price:") : results[0].find("Price:") + 20],
    )

    # Extract title
    regex_filter = RegexContentFilter(pattern=r'<h1 id="product-title">(.*?)</h1>')
    results = regex_filter.filter_content(HTML)
    print("Title (extracted):", results)

    # Test with ContentFilter wrapper
    filter_wrapper = ContentFilter(
        filter_type="regex",
        pattern=r'<div class="product-description">\s*(.*?)\s*</div>',
    )
    results = filter_wrapper.filter_content(HTML)
    print("Description (via wrapper):", results)


if __name__ == "__main__":
    # Run the tests
    test_css_filter()
    test_xpath_filter()
    test_regex_filter()
