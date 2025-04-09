# Project Rules: E-commerce Product Data Extraction System

### 🔄 Project Awareness & Context

- **Always read `PLANNING.md`** at the start of a new conversation to understand the project's architecture, extraction strategies, and technical constraints.
- **Check `TASK.md`** before starting a new task. If the task isn't listed, add it with a brief description and today's date.
- **Use consistent naming conventions and architecture patterns** as described in `PLANNING.md`, particularly around the extraction approach hierarchy.
- **Maintain awareness of the distinction** between CSS/XPath extraction and LLM-based extraction strategies.
- **Reference documentation links** in `PLANNING.md` when implementing specific features.

### 🧱 Code Structure & Modularity

- **Never create a file longer than 500 lines of code.** If a file approaches this limit, refactor by splitting it into modules or helper files.
- **Organize code into clearly separated modules**:
  - `crawler/` - Core crawler functionality
  - `extraction/` - Extraction strategies and schema generators
  - `processing/` - Data cleaning and normalization
  - `storage/` - Database and caching operations
  - `api/` - API endpoints and interfaces
- **Use clear, consistent imports** (prefer relative imports within packages).
- **Keep extraction strategies decoupled** from site-specific code to maintain flexibility.

### 🧪 Testing & Reliability

- **Always create Pytest unit tests for new features** (functions, classes, routes, etc).
- **Create integration tests for each extraction strategy** against sample HTML from different e-commerce sites.
- **Tests should live in a `/tests` folder** mirroring the main app structure.
  - Include at least:
    - 1 test for expected use
    - 1 edge case (e.g., missing product data)
    - 1 failure case (e.g., site structure changes)
- **Create mock HTML fixtures** for testing extraction without API calls.
- **Benchmark extraction performance** for different strategies and site types.

### ✅ Task Completion

- **Mark completed tasks in `TASK.md`** immediately after finishing them.
- **Add new sub-tasks or TODOs** discovered during development to `TASK.md`.
- **Document any site-specific quirks** that were encountered during extraction implementation.
- **Track extraction success rates** for different sites and strategies.

### 📎 Style & Conventions

- **Use Python** as the primary language.
- **Follow PEP8**, use type hints, and format with `black`.
- **Use `pydantic` for data models** and extraction schemas.
- **Use async/await patterns** consistently with Crawl4AI's asynchronous API.
- **Standardize error handling** across extraction strategies.
- Write **docstrings for every function** using the Google style:

  ```python
  async def extract_product_data(url: str, strategy: ExtractionStrategy) -> ProductData:
      """
      Extract product data from a given URL using the specified strategy.

      Args:
          url (str): The product page URL to extract from.
          strategy (ExtractionStrategy): The extraction strategy to use.

      Returns:
          ProductData: Extracted and validated product information.

      Raises:
          ExtractionError: If extraction fails or required fields are missing.
      """
  ```

### 📚 Documentation & Explainability

- **Update `README.md`** when new features are added, dependencies change, or setup steps are modified.
- **Document LLM prompts separately** in a `prompts/` directory with explanations.
- **Include examples for each extraction strategy** in the documentation.
- **Comment non-obvious code**, especially around site-specific workarounds.
- When implementing complex extraction logic, **add an inline `# Reason:` comment** explaining the rationale.
- **Document token usage and costs** for LLM-based strategies.

### 🧠 AI Behavior Rules

- **Never assume missing context. Ask questions if uncertain about site structure.**
- **Never hallucinate libraries or functions** – use only documented Crawl4AI features.
- **Always confirm file paths and module names** exist before referencing them in code or tests.
- **Never delete or overwrite existing extraction strategies** unless explicitly instructed to.
- **Don't assume CSS selectors will work across sites** - leverage the Automated Schema Generator.
- **Be transparent about LLM limitations** for certain types of product data extraction.

### 📚 Documentation References

- **Consult Crawl4AI documentation** @docs.crawl4ai for extraction strategy implementation details.
- **Reference Pydantic documentation** @docs.pydantic when creating data models for extraction.
- **Always check version compatibility** between libraries before implementation.
- **Document any deviations** from standard library usage with explanations.
- **Maintain links to specific documentation sections** for complex implementations.
- **For specific selectors or extraction issues**, reference the appropriate documentation section.
- **Keep a log of undocumented behaviors** and contribute fixes where possible.

### 🌐 Crawl4AI-Specific Guidelines

- **Cache generated schemas** to reduce LLM usage and improve performance.
- **Implement proper rate limiting** to avoid overloading target sites.
- **Handle site-specific authentication** where needed using Crawl4AI's hooking capabilities.
- **Test both headless and headed browser modes** for sites with complex JavaScript.
- **Monitor extraction quality metrics** by strategy type and target site.
- **Prefer the fastest extraction method** that meets accuracy requirements.
- **Implement proper error handling** for common Crawl4AI exceptions.
