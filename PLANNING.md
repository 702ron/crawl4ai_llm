# E-commerce Product Data Extraction System

## Vision
Build a robust, scalable system for extracting product information (title, description, price, UPC codes, etc.) from various e-commerce and product information websites without requiring prior knowledge of site-specific CSS selectors or structure.

## Goals
- Extract comprehensive product data including title, description, price, UPC/EAN/ISBN codes, SKUs, images, and other relevant attributes
- Support a wide range of e-commerce sites without site-specific configurations
- Process data at scale with high accuracy and reliability
- Minimize manual intervention and maintenance

## Documentation References
- Crawl4AI Documentation (v0.5.x): https://docs.crawl4ai.com/
  - Extraction Strategies: https://docs.crawl4ai.com/extraction/overview/
  - Schema Generation: https://docs.crawl4ai.com/extraction/no-llm-strategies/
  - LLM Strategies: https://docs.crawl4ai.com/extraction/llm-strategies/
  - Clustering Strategies: https://docs.crawl4ai.com/extraction/clustring-strategies/
  - API Reference: https://docs.crawl4ai.com/api/strategies/
- Pydantic Documentation (v2.x): https://docs.pydantic.dev/
  - Schema Models: https://docs.pydantic.dev/latest/usage/models/
  - Field Types: https://docs.pydantic.dev/latest/api/fields/
  - Validators: https://docs.pydantic.dev/latest/api/functional_validators/

## Architecture
The system will use a modular architecture with the following components:

1. **Crawler Manager**: Orchestrates the crawling process and manages site-specific sessions
2. **Extraction Engine**: Handles the extraction of product data using LLM-assisted approaches
3. **Data Processor**: Cleans, normalizes, and validates the extracted data
4. **Storage Layer**: Persists the extracted data in a structured format
5. **API Layer**: Provides endpoints for triggering extractions and retrieving data

## Technical Constraints
- Must work across diverse e-commerce sites with varying structures
- Must handle dynamic content loaded via JavaScript
- Must respect robots.txt and implement rate limiting
- Should be resilient to site changes and structure updates
- Should minimize LLM usage costs while maintaining accuracy

## Tech Stack
- **Primary Extraction Tool**: Crawl4AI
- **Programming Language**: Python
- **LLM Providers**: OpenAI GPT-4, Anthropic Claude (via Crawl4AI integrations)
- **Database**: PostgreSQL for structured data, MongoDB for raw extraction results
- **Containerization**: Docker for deployment
- **Orchestration**: Airflow for scheduling and workflow management
- **Monitoring**: Prometheus and Grafana

## Extraction Strategy
Based on the constraints (unknown selectors across various sites), we'll use the following approaches:

1. **Primary Approach**: Automated Schema Generation
   - Use Crawl4AI's JsonCssExtractionStrategy.generate_schema to dynamically create extraction schemas
   - LLM will analyze the site structure and generate appropriate selectors
   - Generated schemas will be cached and reused for similar pages

2. **Fallback Approach**: LLM Extraction Strategy
   - For sites where automated schema generation doesn't work well
   - Direct LLM-based extraction using Pydantic models to define the expected data structure
   - More flexible but potentially higher cost

3. **Metadata Extraction**:
   - Leverage Crawl4AI's built-in metadata extraction for supplementary information

## Performance Considerations
- Implement caching at multiple levels (HTML, generated schemas, extraction results)
- Use parallel processing for high-volume extraction
- Implement adaptive rate limiting based on site response
- Monitor and optimize LLM token usage

## Security & Compliance
- Respect robots.txt and site terms of service
- Implement proper user-agent identification
- Store only public product information
- Implement data retention policies as needed

## Evaluation Metrics
- Extraction success rate (% of products successfully extracted)
- Data completeness (% of expected fields populated)
- Processing time per product
- Cost per product (especially LLM costs)
- Error rates and failure modes

Use this PLANNING.md as the foundation for implementing the e-commerce product data extraction system. Any architectural decisions should be aligned with the vision, constraints, and approaches outlined in this document.
