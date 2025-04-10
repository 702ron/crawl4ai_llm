# Crawl4AI LLM Examples

This directory contains example scripts demonstrating how to use the Crawl4AI LLM library for e-commerce product data extraction.

## Available Examples

- **SDK Client Example**: Demonstrates how to use the SDK client library to extract, manage, search, and export product data (`sdk_client_example.py`)
- **Batch Extraction Example**: Shows how to extract product data from multiple URLs in parallel (`batch_extraction_example.py`)
- **Sample URL File**: A collection of sample product URLs for use with the batch extraction example (`sample_urls.txt`)

## Client Library Documentation

For comprehensive documentation on the client library, please refer to the [Client Library README](../crawl4ai_llm/client/README.md) file.

## Usage

To run the examples, you'll need to have the Crawl4AI LLM package installed:

```bash
pip install crawl4ai_llm
```

Then, you can run any example using Python:

```bash
python sdk_client_example.py
```

Some examples may require additional arguments or configuration. Check the comments at the top of each file for specific instructions.

## Batch Extraction Example

The `batch_extraction_example.py` script demonstrates how to extract product data from multiple URLs in batch mode.

### Usage:

```bash
# Run with default settings
python batch_extraction_example.py -i example_urls.txt -o results.json

# Run with CSV output
python batch_extraction_example.py -i example_urls.txt -o results.csv --format csv

# Run with custom concurrency
python batch_extraction_example.py -i example_urls.txt -o results.json --concurrency 5

# Get help
python batch_extraction_example.py --help
```

### Input File Format

The input file should contain one URL per line. Empty lines are ignored.

### Output Formats

- **JSON**: Each product is saved as a JSON object in an array
- **CSV**: Products are flattened and saved in CSV format with headers

## API Usage Example

The `api_usage_example.py` script demonstrates how to use the Crawl4AI LLM package directly in your Python code.

### Usage:

```bash
# Run the example
python api_usage_example.py
```

The script demonstrates three extraction methods:

- Auto schema generation
- Custom filter chain extraction
- LLM-based extraction (commented out by default)

## Content Filter Example

The `content_filter_example.py` script demonstrates advanced content filtering techniques using different filter types and chain strategies.

### Usage:

```bash
# Run with default Amazon URL
python content_filter_example.py

# Run with a custom URL
python content_filter_example.py https://www.example-shop.com/products/123
```

### Features Demonstrated:

- Individual filter types (BM25, Pruning, CSS, Regex)
- Filter chain strategies (SEQUENCE, ALL, ANY)
- Mixed filter type chains
- Nested filter chains
- Optimized filter configuration for product extraction

The script outputs comparison information about each filter type and strategy, and saves the extracted product data to a JSON file.

## Schema Generator Example

The `schema_generator_example.py` script demonstrates how to generate, validate, and test extraction schemas for e-commerce websites.

### Usage:

```bash
# Generate a schema for a URL
python schema_generator_example.py https://www.example-shop.com/products/123

# Generate a schema and test it
python schema_generator_example.py https://www.example-shop.com/products/123 --test

# Use an existing schema file
python schema_generator_example.py --schema my_schema.json --test

# Compare with auto schema extraction
python schema_generator_example.py --compare

# Get help
python schema_generator_example.py --help
```

### Features Demonstrated:

- Schema generation for product pages
- Schema validation and auto-correction
- Quality reporting for schemas
- Testing schemas with real extraction
- Comparing with auto schema generation

The script generates detailed output about the schema and saves both the schema and extracted product data to JSON files.

## SDK Client Example

The `sdk_client_example.py` script demonstrates how to use the Python SDK/client library to interact with the Crawl4AI LLM API.

### Usage:

```bash
# Set your API key (or configure in the script)
export CRAWL4AI_API_KEY="your_api_key_here"

# Optional: Set API URL (defaults to localhost)
export CRAWL4AI_API_URL="http://localhost:8000"

# Run the example
python sdk_client_example.py
```

### Features Demonstrated:

- Initializing the client with authentication
- Single product extraction
- Batch extraction from multiple URLs
- Product management operations (get, update)
- Product search with filtering
- Exporting products to JSON and CSV formats
- Error handling and retry logic

The script demonstrates a complete workflow from extraction to management and export using the SDK client library.

### Key Benefits of the SDK:

- **Fully Typed**: Complete type hints for better IDE integration and error catching
- **Async API**: Built on `aiohttp` for efficient asynchronous operations
- **Concurrency Control**: Manage parallel requests with semaphores
- **Structured Data**: Pydantic models for request and response data
- **Robust Error Handling**: Automatic retries with exponential backoff
- **Resource Management**: Proper session handling with context management

### Example Code Snippet:

```python
from crawl4ai_llm.client import Crawl4AIClient
from crawl4ai_llm.client.models import ExtractionRequest

async def extract_example():
    client = Crawl4AIClient(api_key="your_api_key_here")

    try:
        # Create an extraction request
        request = ExtractionRequest(
            url="https://www.amazon.com/dp/B08F7CJQZ3",
            extraction_method="auto",
            use_fallback=True,
            store_result=True
        )

        # Extract the product
        result = await client.extract_product(request)

        if result.success:
            print(f"Extracted: {result.product.title}")
            print(f"Product ID: {result.product_id}")
        else:
            print(f"Extraction failed: {result.error}")
    finally:
        await client.close()
```

## API Server

The package includes a REST API server for extracting product data. Use the `start_api_server.py` script to manage the server:

```bash
# Start the API server
python start_api_server.py start --host 0.0.0.0 --port 8000

# Create an admin user
python start_api_server.py create-admin --username admin --rate-limit 120
```

## API Example

The package provides a command-line API that can be used directly:

```bash
# Extract a single product
crawl4ai-api extract https://www.amazon.com/Apple-MacBook-16-inch-10%E2%80%91core-16%E2%80%91core/dp/B09JQSLL92/

# Use a specific extraction method
crawl4ai-api extract --method llm https://www.amazon.com/Apple-MacBook-16-inch-10%E2%80%91core-16%E2%80%91core/dp/B09JQSLL92/

# Save output to a file
crawl4ai-api extract --output product_data.json https://www.amazon.com/Apple-MacBook-16-inch-10%E2%80%91core-16%E2%80%91core/dp/B09JQSLL92/
```

## Requirements

Make sure you have set your API key as an environment variable:

```bash
export CRAWL4AI_API_KEY="your_api_key_here"
```

Or pass it as a command-line argument:

```bash
python batch_extraction_example.py -i example_urls.txt -o results.json --api-key "your_api_key_here"
```

## Transaction Example

This example demonstrates how to use the transaction support in the storage layer for atomic operations.

### Usage:

```bash
# Run the transaction example
python transaction_example.py
```

### Features Demonstrated:

- Simple transactions with multiple operations
- Transaction rollback on errors
- Batch operations within transactions
- Complex multi-operation transactions
- Transaction-based cleanup

The script creates sample products, performs various transaction operations, and cleans up after itself.

Output includes detailed information about each transaction step, verification of changes, and cleanup operations.
