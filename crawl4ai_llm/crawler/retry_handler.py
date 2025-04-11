"""
Retry handler for request retries with configurable backoff strategies.

This module provides a robust retry mechanism for handling transient failures
in web requests, with support for different backoff strategies and customizable
retry conditions.
"""

import asyncio
import logging
import random
import time
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union, TypeVar, cast

logger = logging.getLogger(__name__)

# Type definitions for better type hints
T = TypeVar('T')
RetryConditionType = Callable[[Any], bool]
DelayStrategyType = Callable[[int, float, float, float], float]


class RetryStrategy:
    """
    Enumeration of available retry delay strategies.
    """
    FIXED = "fixed"  # Fixed delay between retries
    LINEAR = "linear"  # Linear increase in delay
    EXPONENTIAL = "exponential"  # Exponential backoff
    FIBONACCI = "fibonacci"  # Fibonacci sequence for delay


class RetryHandler:
    """
    Handler for retrying operations with configurable backoff strategies.
    
    This class provides a flexible way to handle retries with different
    backoff strategies, jitter, and custom retry conditions.
    """

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        strategy: str = RetryStrategy.EXPONENTIAL,
        backoff_factor: float = 1.5,
        jitter: float = 0.5,
        retry_codes: Optional[List[int]] = None,
        retry_exceptions: Optional[List[Exception]] = None,
        retry_condition: Optional[RetryConditionType] = None,
    ):
        """
        Initialize the retry handler with configurable settings.

        Args:
            max_retries: Maximum number of retry attempts.
            retry_delay: Base delay between retries in seconds.
            strategy: Backoff strategy to use (fixed, linear, exponential, fibonacci).
            backoff_factor: Multiplication factor for backoff calculation.
            jitter: Random jitter factor to add to retry delays (0-1).
            retry_codes: HTTP status codes that should trigger a retry.
            retry_exceptions: Exception types that should trigger a retry.
            retry_condition: Custom function to determine if a result should trigger a retry.
                             Function takes a result and returns True if retry is needed.
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.strategy = strategy
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.retry_codes = retry_codes or [408, 429, 500, 502, 503, 504]
        self.retry_exceptions = tuple(retry_exceptions or [
            ConnectionError,
            TimeoutError,
        ])
        self.retry_condition = retry_condition or self._default_retry_condition
        # Track the number of remaining attempts
        self.attempts_remaining = max_retries

    def _default_retry_condition(self, result: Any) -> bool:
        """
        Default condition to determine if a request should be retried.
        
        Args:
            result: The result from an operation.
            
        Returns:
            True if the operation should be retried, False otherwise.
        """
        # Handle None result
        if result is None:
            return True
            
        # Handle dict-like results with status or success keys
        if isinstance(result, dict):
            # Check for HTTP status code
            if 'status_code' in result and result['status_code'] in self.retry_codes:
                return True
                
            if 'status' in result and isinstance(result['status'], int) and result['status'] in self.retry_codes:
                return True
                
            # Check for success flag
            if 'success' in result and result['success'] is False:
                return True
                
            # Check for HTML content in crawl results
            if 'html' in result:
                html = result.get('html', '')
                if not html or (isinstance(html, str) and len(html) < 500):
                    return True
                    
        return False

    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay before next retry based on the selected strategy.
        
        Args:
            attempt: The current retry attempt number (0-indexed).
            
        Returns:
            Delay in seconds before next retry.
        """
        if self.strategy == RetryStrategy.FIXED:
            # Fixed delay for all retries
            delay = self.retry_delay
            
        elif self.strategy == RetryStrategy.LINEAR:
            # Linear increase in delay
            delay = self.retry_delay * (1 + attempt * self.backoff_factor)
            
        elif self.strategy == RetryStrategy.EXPONENTIAL:
            # Exponential backoff
            delay = self.retry_delay * (self.backoff_factor ** attempt)
            
        elif self.strategy == RetryStrategy.FIBONACCI:
            # Fibonacci sequence
            # Calculate nth Fibonacci number (starting from attempt=0)
            def fib(n: int) -> int:
                a, b = 1, 1
                for _ in range(n):
                    a, b = b, a + b
                return a
                
            delay = self.retry_delay * fib(attempt + 1)  # +1 because attempt is 0-indexed
        
        else:
            # Default to exponential backoff
            delay = self.retry_delay * (self.backoff_factor ** attempt)
            
        # Add random jitter
        if self.jitter > 0:
            jitter_amount = random.uniform(0, self.jitter * delay)
            delay += jitter_amount
            
        return delay

    async def execute(
        self, 
        func: Callable[..., Any], 
        *args: Any, 
        **kwargs: Any
    ) -> Any:
        """
        Execute a function with retry logic.

        Args:
            func: The function to execute.
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            The result of the function call.

        Raises:
            Exception: The last exception raised by the function if all retries fail.
        """
        attempt = 0
        last_exception = None
        result = None
        
        # Reset attempts_remaining at the start of execution
        self.attempts_remaining = self.max_retries

        while attempt <= self.max_retries:
            try:
                if attempt > 0:
                    # Calculate and wait for retry delay
                    delay = self._calculate_delay(attempt - 1)
                    logger.info(f"Retry {attempt}/{self.max_retries} in {delay:.2f} seconds")
                    await asyncio.sleep(delay)
                    # Update attempts_remaining
                    self.attempts_remaining = self.max_retries - attempt

                # Call the function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # Check if we need to retry based on the result
                if not self.retry_condition(result):
                    # Success or no need to retry
                    return result

                logger.warning(f"Retry condition triggered (attempt {attempt+1}/{self.max_retries+1})")

            except self.retry_exceptions as e:
                last_exception = e
                logger.error(f"Retryable error (attempt {attempt+1}/{self.max_retries+1}): {str(e)}")
            except Exception as e:
                # Non-retryable exception
                logger.error(f"Non-retryable error: {str(e)}")
                raise

            # Increment attempt counter
            attempt += 1
            # Update attempts_remaining
            self.attempts_remaining = self.max_retries - attempt

        # If we've exhausted all retries and still have no result
        if last_exception:
            logger.error(f"Failed after {self.max_retries} retries. Last error: {str(last_exception)}")
            raise last_exception

        # If we have a result but it didn't meet our success criteria
        logger.warning(f"Operation partially succeeded but didn't meet success criteria after {attempt} attempts")
        return result

    def retry(
        self, 
        max_retries: Optional[int] = None, 
        retry_condition: Optional[RetryConditionType] = None
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """
        Decorator to add retry logic to a function.

        Args:
            max_retries: Override the default max_retries for this specific function.
            retry_condition: Override the default retry_condition for this specific function.

        Returns:
            Decorated function with retry logic.
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> T:
                # Use overridden values or instance defaults
                _max_retries = max_retries if max_retries is not None else self.max_retries
                _retry_condition = retry_condition or self.retry_condition
                
                # Create a temporary handler with the overridden values
                temp_handler = RetryHandler(
                    max_retries=_max_retries,
                    retry_delay=self.retry_delay,
                    strategy=self.strategy,
                    backoff_factor=self.backoff_factor,
                    jitter=self.jitter,
                    retry_codes=self.retry_codes,
                    retry_condition=_retry_condition,
                )
                
                # Execute with retry logic
                result = await temp_handler.execute(func, *args, **kwargs)
                
                # Copy the attempts_remaining back to the parent handler for tracking
                self.attempts_remaining = temp_handler.attempts_remaining
                
                return cast(T, result)
                
            return wrapper
        return decorator


# Utility functions for common retry strategies
def create_fixed_retry_handler(
    max_retries: int = 3, 
    delay: float = 2.0, 
    jitter: float = 0.0
) -> RetryHandler:
    """Create a retry handler with fixed delay strategy."""
    return RetryHandler(
        max_retries=max_retries,
        retry_delay=delay,
        strategy=RetryStrategy.FIXED,
        jitter=jitter
    )


def create_exponential_retry_handler(
    max_retries: int = 3, 
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0, 
    jitter: float = 0.1
) -> RetryHandler:
    """Create a retry handler with exponential backoff strategy."""
    return RetryHandler(
        max_retries=max_retries,
        retry_delay=initial_delay,
        strategy=RetryStrategy.EXPONENTIAL,
        backoff_factor=backoff_factor,
        jitter=jitter
    )


def create_fibonacci_retry_handler(
    max_retries: int = 5, 
    base_delay: float = 1.0, 
    jitter: float = 0.2
) -> RetryHandler:
    """Create a retry handler with Fibonacci sequence delay strategy."""
    return RetryHandler(
        max_retries=max_retries,
        retry_delay=base_delay,
        strategy=RetryStrategy.FIBONACCI,
        jitter=jitter
    )

# Aliases for backward compatibility
create_fixed_retry = create_fixed_retry_handler
create_exponential_retry = create_exponential_retry_handler
create_fibonacci_retry = create_fibonacci_retry_handler 