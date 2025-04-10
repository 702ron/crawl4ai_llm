# Integration Test Data

This directory contains test data and fixtures for integration tests in the Crawl4AI LLM package.

## Directory Structure

- `benchmark_fixtures.json`: Contains benchmark product URLs and expected data for validation
- `results/`: Directory for test run results and metrics
  - `benchmark_results.json`: Results from benchmark tests in JSON format
  - `benchmark_results.csv`: Results from benchmark tests in CSV format
  - `performance_metrics.json`: Performance metrics from extraction tests
  - `js_comparison.json`: Comparison of JS-enabled vs JS-disabled extraction

## Adding Test Data

To add new benchmark products:

1. Choose stable product URLs that are unlikely to change frequently
2. Define expected data for validation (title, brand, price ranges, etc.)
3. Add entries to the `BENCHMARK_PRODUCTS` list in `test_benchmark.py`

## Running Benchmarks

By default, benchmark tests run during normal test execution. To skip benchmarks:

```bash
# Skip benchmarks during testing
SKIP_BENCHMARKS=true python -m unittest discover tests/integration
```

## Analyzing Results

The benchmark results and performance metrics are saved in the `results/` directory after each test run. Use these files to:

1. Track performance over time
2. Identify extraction issues with specific sites
3. Compare different extraction configurations
4. Measure the impact of code changes on extraction performance

For visual analysis, you can import the CSV files into spreadsheet software or data visualization tools.
