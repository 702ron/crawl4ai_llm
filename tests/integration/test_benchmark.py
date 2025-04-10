"""Benchmarking and validation tests for product extraction.

This module contains benchmark tests that:
1. Measure extraction performance across different sites
2. Validate extraction results against expected data
3. Compare JS-enabled and JS-disabled extraction
4. Track performance metrics over time
"""

import asyncio
import csv
import json
import os
import time
import unittest
from datetime import datetime
from statistics import mean, median

from crawl4ai_llm.extraction import ProductExtractor
from crawl4ai_llm.models import ProductData

# Directory for test data
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "test_data")
RESULTS_DIR = os.path.join(TEST_DATA_DIR, "results")
BENCHMARK_FILE = os.path.join(TEST_DATA_DIR, "benchmark_fixtures.json")
BENCHMARK_RESULTS_JSON = os.path.join(RESULTS_DIR, "benchmark_results.json")
BENCHMARK_RESULTS_CSV = os.path.join(RESULTS_DIR, "benchmark_results.csv")
PERFORMANCE_METRICS = os.path.join(RESULTS_DIR, "performance_metrics.json")
JS_COMPARISON = os.path.join(RESULTS_DIR, "js_comparison.json")

# Ensure directories exist
os.makedirs(RESULTS_DIR, exist_ok=True)

# List of benchmark products with expected data
BENCHMARK_PRODUCTS = [
    {
        "url": "https://www.amazon.com/Apple-iPhone-13-Pro-Max/dp/B09G9HD6PD",
        "expected": {
            "title": "iPhone 13 Pro Max",
            "brand": "Apple",
            "price_min": 999,
            "price_max": 1599,
            "category": ["Electronics", "Cell Phones"]
        }
    },
    {
        "url": "https://www.bestbuy.com/site/sony-wh-1000xm4-wireless-noise-cancelling-over-the-ear-headphones-black/6408356.p",
        "expected": {
            "title": "Sony WH-1000XM4",
            "brand": "Sony",
            "price_min": 249,
            "price_max": 349,
            "category": ["Audio", "Headphones"]
        }
    },
    {
        "url": "https://www.walmart.com/ip/LEGO-Star-Wars-The-Mandalorian-The-Razor-Crest-75292-Building-Toy/949767353",
        "expected": {
            "title": "LEGO Star Wars: The Mandalorian The Razor Crest",
            "brand": "LEGO",
            "price_min": 120,
            "price_max": 170,
            "category": ["Toys", "Building Sets"]
        }
    },
    {
        "url": "https://www.target.com/p/ninja-foodi-smart-xl-6-in-1-indoor-grill-with-air-fryer-roast-bake-broil-dehydrate-fg551/-/A-79775414",
        "expected": {
            "title": "Ninja Foodi Smart XL 6-in-1 Indoor Grill",
            "brand": "Ninja",
            "price_min": 249,
            "price_max": 329,
            "category": ["Kitchen", "Small Appliances"]
        }
    },
    {
        "url": "https://www.bhphotovideo.com/c/product/1566323-REG/fujifilm_x_t4_mirrorless_digital_camera.html",
        "expected": {
            "title": "FUJIFILM X-T4 Mirrorless Digital Camera",
            "brand": "FUJIFILM",
            "price_min": 1499,
            "price_max": 1899,
            "category": ["Photography", "Cameras"]
        }
    }
]

def create_fixtures_file():
    """Create a fixtures file if it doesn't exist."""
    if not os.path.exists(BENCHMARK_FILE):
        with open(BENCHMARK_FILE, 'w') as f:
            json.dump(BENCHMARK_PRODUCTS, f, indent=2)
        print(f"Created benchmark fixtures file: {BENCHMARK_FILE}")

class TestBenchmarkPerformance(unittest.TestCase):
    """Test benchmarking and validation of product extraction."""
    
    @classmethod
    def setUpClass(cls):
        """Set up the test environment."""
        create_fixtures_file()
        cls.extractor = ProductExtractor()
        cls.extractor_js = ProductExtractor(enable_javascript=True)
        
        # Load benchmark products
        if os.path.exists(BENCHMARK_FILE):
            with open(BENCHMARK_FILE, 'r') as f:
                cls.benchmark_products = json.load(f)
        else:
            cls.benchmark_products = BENCHMARK_PRODUCTS
            
        cls.results = {}
        cls.metrics = {
            "timestamp": datetime.now().isoformat(),
            "total_products": len(cls.benchmark_products),
            "extraction_times": [],
            "success_rate": 0,
            "validation_results": []
        }
        
        cls.js_comparison = {
            "timestamp": datetime.now().isoformat(),
            "comparisons": []
        }
    
    async def extract_product(self, url, enable_js=False):
        """Extract product data from URL."""
        start_time = time.time()
        extractor = self.extractor_js if enable_js else self.extractor
        
        try:
            product = await extractor.extract(url)
            extraction_time = time.time() - start_time
            
            return {
                "url": url,
                "success": product is not None,
                "extraction_time": extraction_time,
                "product": product.dict() if product else None
            }
        except Exception as e:
            extraction_time = time.time() - start_time
            return {
                "url": url,
                "success": False,
                "extraction_time": extraction_time,
                "error": str(e),
                "product": None
            }
    
    def validate_product(self, result, expected):
        """Validate extracted product against expected data."""
        if not result.get("success") or not result.get("product"):
            return {
                "url": result["url"],
                "valid": False,
                "reason": "Extraction failed"
            }
        
        product = result["product"]
        validation = {
            "url": result["url"],
            "valid": True,
            "checks": []
        }
        
        # Check title
        if "title" in expected:
            title_valid = expected["title"].lower() in product["title"].lower()
            validation["checks"].append({
                "field": "title",
                "valid": title_valid,
                "expected": expected["title"],
                "actual": product["title"]
            })
            if not title_valid:
                validation["valid"] = False
        
        # Check brand
        if "brand" in expected and product.get("brand"):
            brand_valid = expected["brand"].lower() in product["brand"].lower()
            validation["checks"].append({
                "field": "brand",
                "valid": brand_valid,
                "expected": expected["brand"],
                "actual": product["brand"]
            })
            if not brand_valid:
                validation["valid"] = False
        
        # Check price range
        if "price_min" in expected and "price_max" in expected and "price" in product:
            price_value = float(product["price"]["amount"])
            price_valid = expected["price_min"] <= price_value <= expected["price_max"]
            validation["checks"].append({
                "field": "price",
                "valid": price_valid,
                "expected": f"{expected['price_min']} - {expected['price_max']}",
                "actual": price_value
            })
            if not price_valid:
                validation["valid"] = False
        
        # Check category
        if "category" in expected and "categories" in product:
            category_valid = any(exp_cat.lower() in ' '.join(product["categories"]).lower() 
                                for exp_cat in expected["category"])
            validation["checks"].append({
                "field": "category",
                "valid": category_valid,
                "expected": expected["category"],
                "actual": product.get("categories", [])
            })
            if not category_valid:
                validation["valid"] = False
        
        return validation
    
    def save_benchmark_results(self):
        """Save benchmark results to files."""
        # Save as JSON
        with open(BENCHMARK_RESULTS_JSON, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Save as CSV
        with open(BENCHMARK_RESULTS_CSV, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "URL", "Success", "Extraction Time (s)", 
                "Valid", "Title", "Brand", "Price", "Categories"
            ])
            
            for url, result in self.results.items():
                product = result.get("product", {})
                writer.writerow([
                    url,
                    result.get("success", False),
                    f"{result.get('extraction_time', 0):.2f}",
                    result.get("validation", {}).get("valid", False),
                    product.get("title", ""),
                    product.get("brand", ""),
                    f"{product.get('price', {}).get('amount', '')} {product.get('price', {}).get('currency', '')}",
                    ", ".join(product.get("categories", []))
                ])
        
        # Save metrics
        with open(PERFORMANCE_METRICS, 'w') as f:
            json.dump(self.metrics, f, indent=2)
        
        # Save JS comparison
        with open(JS_COMPARISON, 'w') as f:
            json.dump(self.js_comparison, f, indent=2)
    
    def report_metrics(self):
        """Report performance metrics."""
        extraction_times = self.metrics["extraction_times"]
        
        if extraction_times:
            avg_time = mean(extraction_times)
            median_time = median(extraction_times)
            min_time = min(extraction_times)
            max_time = max(extraction_times)
            
            print(f"\nPerformance Metrics:")
            print(f"Total Products: {self.metrics['total_products']}")
            print(f"Success Rate: {self.metrics['success_rate']:.2f}%")
            print(f"Validation Success: {sum(1 for r in self.metrics['validation_results'] if r['valid'])}/{len(self.metrics['validation_results'])}")
            print(f"Average Extraction Time: {avg_time:.2f}s")
            print(f"Median Extraction Time: {median_time:.2f}s")
            print(f"Min/Max Extraction Time: {min_time:.2f}s / {max_time:.2f}s")
    
    def test_benchmark_extraction(self):
        """Test extraction performance and validation for benchmark products."""
        # Skip if environment variable is set
        if os.environ.get("SKIP_BENCHMARKS") == "true":
            self.skipTest("Skipping benchmarks due to SKIP_BENCHMARKS=true")
        
        # Extract products
        for product_data in self.benchmark_products:
            url = product_data["url"]
            expected = product_data["expected"]
            
            result = asyncio.run(self.extract_product(url))
            self.results[url] = result
            
            # Update metrics
            if result["extraction_time"]:
                self.metrics["extraction_times"].append(result["extraction_time"])
            
            # Validate product
            validation = self.validate_product(result, expected)
            self.results[url]["validation"] = validation
            self.metrics["validation_results"].append(validation)
        
        # Calculate success rate
        successful = sum(1 for r in self.results.values() if r["success"])
        self.metrics["success_rate"] = (successful / len(self.benchmark_products)) * 100
        
        # Save results
        self.save_benchmark_results()
        
        # Report metrics
        self.report_metrics()
        
        # Assert minimum success rate
        self.assertGreaterEqual(
            self.metrics["success_rate"], 
            60.0,  # Minimum 60% success rate
            "Extraction success rate below threshold"
        )
    
    def test_js_vs_no_js_extraction(self):
        """Test and compare JS-enabled vs JS-disabled extraction."""
        # Skip if environment variable is set
        if os.environ.get("SKIP_BENCHMARKS") == "true" or os.environ.get("SKIP_JS_TESTS") == "true":
            self.skipTest("Skipping JS comparison tests")
        
        # Choose subset of products for JS testing (to save time)
        js_test_products = self.benchmark_products[:2]
        
        for product_data in js_test_products:
            url = product_data["url"]
            
            # Extract with regular extractor
            regular_result = asyncio.run(self.extract_product(url, enable_js=False))
            
            # Extract with JS-enabled extractor
            js_result = asyncio.run(self.extract_product(url, enable_js=True))
            
            comparison = {
                "url": url,
                "regular_success": regular_result["success"],
                "js_success": js_result["success"],
                "regular_time": regular_result["extraction_time"],
                "js_time": js_result["extraction_time"],
                "time_difference": js_result["extraction_time"] - regular_result["extraction_time"],
                "regular_fields": len(regular_result.get("product", {}).keys()) if regular_result.get("product") else 0,
                "js_fields": len(js_result.get("product", {}).keys()) if js_result.get("product") else 0,
                "field_difference": (
                    len(js_result.get("product", {}).keys()) - len(regular_result.get("product", {}).keys())
                    if js_result.get("product") and regular_result.get("product") else 0
                )
            }
            
            self.js_comparison["comparisons"].append(comparison)
            print(f"\nJS Comparison for {url}:")
            print(f"Regular Extraction: {comparison['regular_success']} in {comparison['regular_time']:.2f}s")
            print(f"JS-Enabled Extraction: {comparison['js_success']} in {comparison['js_time']:.2f}s")
            print(f"Field count difference: {comparison['field_difference']}")
        
        # Save JS comparison results
        with open(JS_COMPARISON, 'w') as f:
            json.dump(self.js_comparison, f, indent=2)

if __name__ == '__main__':
    unittest.main() 