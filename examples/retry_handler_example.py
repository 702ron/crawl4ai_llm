"""
Example demonstrating the use of the RetryHandler in Crawl4AI.

This example shows:
1. Basic retry handler usage with different retry strategies
2. Custom retry conditions
3. Using the retry handler decorator
4. Comparing results from different retry strategies
"""

import asyncio
import logging
import random
import time
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path for importing
sys.path.append(str(Path(__file__).parent.parent))

from crawl4ai_llm.crawler.retry_handler import (
    RetryHandler, RetryStrategy, create_exponential_retry, 
    create_fibonacci_retry, create_fixed_retry
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Simulated function that sometimes fails
async def flaky_function(success_rate=0.3):
    """
    A simulated function that randomly succeeds or fails.
    
    Args:
        success_rate: Probability of success (0.0 to 1.0)
        
    Returns:
        Dict containing result information
    """
    # Simulate a random delay (network latency)
    await asyncio.sleep(random.uniform(0.1, 0.5))
    
    # Randomly succeed or fail
    if random.random() < success_rate:
        logger.info("Function executed successfully")
        return {
            "success": True,
            "data": f"Success data generated at {datetime.now().isoformat()}",
            "timestamp": datetime.now().isoformat(),
        }
    else:
        # Simulate different types of failures
        error_types = [
            "ConnectionError",
            "TimeoutError",
            "RateLimitExceeded",
            "InternalServerError",
        ]
        error = random.choice(error_types)
        logger.info(f"Function failed with error: {error}")
        
        if error == "RateLimitExceeded":
            # This is a special case we'll handle differently
            raise Exception(f"Rate limit exceeded, try again later")
        
        return {
            "success": False,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }

# Custom retry condition
def custom_retry_condition(result):
    """
    Custom retry condition that retries on specific errors.
    
    Args:
        result: Result dictionary from the function
        
    Returns:
        bool: True if should retry, False otherwise
    """
    # Retry if not successful
    if not result.get("success", False):
        error = result.get("error", "")
        
        # Don't retry for "InternalServerError" 
        if error == "InternalServerError":
            logger.info("Not retrying for InternalServerError")
            return False
            
        # Retry for other errors
        logger.info(f"Retrying for error: {error}")
        return True
    
    # Don't retry successful results
    return False

# Function that's decorated with retry
@RetryHandler.with_retry(
    max_retries=3,
    retry_delay=1.0,
    strategy=RetryStrategy.EXPONENTIAL,
    backoff_factor=2.0,
    jitter=0.3,
)
async def decorated_function(success_rate=0.3):
    """Function with built-in retry using decorator"""
    return await flaky_function(success_rate)

async def compare_retry_strategies():
    """
    Compare different retry strategies and their behavior.
    """
    print("\n=== Comparing Retry Strategies ===")
    
    # Create retry handlers with different strategies
    fixed_retry = create_fixed_retry(max_retries=5, retry_delay=1.0)
    exponential_retry = create_exponential_retry(max_retries=5, initial_delay=1.0, backoff_factor=2.0)
    fibonacci_retry = create_fibonacci_retry(max_retries=5, initial_delay=1.0)
    
    # Track retry counts
    strategies = {
        "Fixed": {"handler": fixed_retry, "attempts": 0, "success": False},
        "Exponential": {"handler": exponential_retry, "attempts": 0, "success": False},
        "Fibonacci": {"handler": fibonacci_retry, "attempts": 0, "success": False},
    }
    
    # Run each strategy until success or max retries
    for name, strategy in strategies.items():
        print(f"\nTesting {name} retry strategy:")
        handler = strategy["handler"]
        
        # Create tracking function to count attempts
        async def tracked_function():
            nonlocal strategy
            strategy["attempts"] += 1
            print(f"  Attempt {strategy['attempts']} with {name} strategy")
            result = await flaky_function(success_rate=0.4)
            if result.get("success", False):
                strategy["success"] = True
            return result
        
        # Execute with retry
        try:
            result = await handler.execute(tracked_function)
            print(f"  {name} result: Success after {strategy['attempts']} attempts")
        except Exception as e:
            print(f"  {name} result: Failed after {strategy['attempts']} attempts: {str(e)}")
    
    # Print summary
    print("\nStrategy comparison summary:")
    for name, strategy in strategies.items():
        status = "Succeeded" if strategy["success"] else "Failed"
        print(f"  {name}: {status} after {strategy['attempts']} attempts")

async def main():
    """
    Main example function demonstrating different retry scenarios.
    """
    print("=== Crawl4AI RetryHandler Example ===\n")
    
    # Example 1: Basic retry handler with exponential backoff
    print("Example 1: Basic retry handler with exponential backoff")
    retry_handler = RetryHandler(
        max_retries=3,
        retry_delay=1.0,
        strategy=RetryStrategy.EXPONENTIAL,
        backoff_factor=2.0,
        jitter=0.5,
    )
    
    try:
        # Try to execute the flaky function with retry
        result = await retry_handler.execute(lambda: flaky_function(success_rate=0.3))
        print(f"Result after {3 - retry_handler.attempts_remaining} attempts: {result}\n")
    except Exception as e:
        print(f"Failed after 3 attempts: {str(e)}\n")
        
    # Example 2: Retry with custom retry condition
    print("Example 2: Retry with custom retry condition")
    custom_handler = RetryHandler(
        max_retries=4,
        retry_delay=1.0,
        strategy=RetryStrategy.LINEAR,
        backoff_factor=1.0,
        retry_condition=custom_retry_condition,
    )
    
    try:
        result = await custom_handler.execute(lambda: flaky_function(success_rate=0.3))
        print(f"Result with custom retry condition after {4 - custom_handler.attempts_remaining} attempts: {result}\n")
    except Exception as e:
        print(f"Failed with custom retry condition after 4 attempts: {str(e)}\n")
        
    # Example 3: Using retry decorator
    print("Example 3: Using retry decorator")
    try:
        result = await decorated_function(success_rate=0.3)
        print(f"Result with retry decorator: {result}\n")
    except Exception as e:
        print(f"Failed with retry decorator: {str(e)}\n")
    
    # Example 4: Compare different retry strategies
    await compare_retry_strategies()


if __name__ == "__main__":
    asyncio.run(main()) 