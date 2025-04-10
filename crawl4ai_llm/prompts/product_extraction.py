"""
Prompt templates for product data extraction.
"""

# Prompt for automated schema generation
SCHEMA_GENERATION_PROMPT = """
Generate a comprehensive extraction schema for this e-commerce product page.
Focus on extracting:
1. Product title and description
2. Price information (current price, original price, discounts)
3. Product images
4. Product identifiers (SKU, UPC, EAN, etc.)
5. Brand information
6. Availability status
7. Product attributes and specifications
8. Variants if available
9. Reviews and ratings if available
10. Additional metadata including:
   - Shipping information
   - Warranty details
   - Product dimensions and weight
   - Material composition
   - Seller/manufacturer details
   - Release or launch date

Identify the most reliable selectors for each element.
Pay attention to microdata, RDFa, or other structured data present in the page.
"""

# Prompt for LLM-based direct extraction
LLM_EXTRACTION_PROMPT = """
Extract product information from this e-commerce page according to the provided schema.
Pay special attention to:
1. Product title, brand, and description
2. Price information (current price, original price, currency)
3. Product identifiers (SKU, UPC, EAN, etc.)
4. Images (collect all image URLs)
5. Availability status
6. Specifications and attributes
7. Reviews and ratings (reviewer name, rating, review text, date)
8. Variants (different sizes, colors, etc.)
9. Supplementary metadata such as:
   - Shipping information and options
   - Warranty details
   - Product dimensions and weight
   - Material composition
   - Seller or manufacturer information
   - Product release date

Look for both visible text and metadata in the HTML.
Some important information like UPC codes might be hidden in meta tags or data attributes.
Return the data in the provided schema format exactly.
"""

# Prompt for fallback extraction when schema-based extraction fails
FALLBACK_EXTRACTION_PROMPT = """
This page has proven difficult to extract with schema-based methods.
Extract the product information directly from the HTML and text content.

Focus first on finding:
1. Product title (usually in an h1 or prominent heading)
2. Current price (look for currency symbols, formatting patterns, or price-related CSS classes)
3. Brand name (often near the title or in breadcrumbs)
4. Product images (look for high-resolution images in gallery sections)
5. Product identifiers like SKU, UPC, EAN, etc. (often near the bottom of the page or in metadata)

Then look for supplementary information:
6. Reviews and ratings (look for star icons, review text blocks, or review sections)
7. Product attributes and specifications (often in tables or lists)
8. Shipping and warranty information (usually near the bottom or in tabs)
9. Product dimensions, weight, and materials
10. Release date or product availability information

Be flexible in your approach and look for patterns that are typical in e-commerce pages.
Return the data strictly formatted according to the provided schema.
"""
