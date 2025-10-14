"""Rate limiting implementation for API calls.

This module provides rate limiting with exponential backoff
to comply with data provider rate limits.
"""

import time
from collections import deque
from datetime import datetime
from typing import Callable, TypeVar

from hormax.core.logging_setup import get_logger
from hormax.exceptions import RateLimitError

logger = get_logger(__name__)

T = TypeVar("T")


class RateLimiter:
    """Rate limiter with exponential backoff retry support.

    Attributes:
        requests_per_second: Maximum requests allowed per second.
        max_retries: Maximum number of retry attempts on failure.
    """

    def __init__(self, requests_per_second: float = 5.0, max_retries: int = 3) -> None:
        """Initialize the rate limiter.

        Args:
            requests_per_second: Maximum requests per second.
            max_retries: Maximum retry attempts.
        """
        self.requests_per_second = requests_per_second
        self.max_retries = max_retries
        self.min_interval = 1.0 / requests_per_second
        self.request_times: deque[float] = deque()

    def _wait_if_needed(self) -> None:
        """Wait if necessary to comply with rate limit."""
        now = time.time()

        # Remove timestamps older than 1 second
        while self.request_times and now - self.request_times[0] > 1.0:
            self.request_times.popleft()

        # If we've hit the limit, wait
        if len(self.request_times) >= self.requests_per_second:
            sleep_time = 1.0 - (now - self.request_times[0])
            if sleep_time > 0:
                logger.debug(f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)
                now = time.time()

        # Record this request
        self.request_times.append(now)

    def execute_with_retry(self, func: Callable[[], T]) -> T:
        """Execute a function with rate limiting and retry on failure.

        Args:
            func: Function to execute.

        Returns:
            Result from the function.

        Raises:
            RateLimitError: If all retry attempts fail.
        """
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                # Wait if needed before making request
                self._wait_if_needed()

                # Execute the function
                result = func()
                return result

            except Exception as e:
                last_error = e

                if attempt < self.max_retries:
                    # Exponential backoff: 1s, 2s, 4s, ...
                    backoff_seconds = 2**attempt
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}. "
                        f"Retrying in {backoff_seconds}s..."
                    )
                    time.sleep(backoff_seconds)
                else:
                    logger.error(
                        f"Request failed after {self.max_retries + 1} attempts: {e}"
                    )

        raise RateLimitError(
            f"Request failed after {self.max_retries + 1} attempts: {last_error}"
        ) from last_error

    def reset(self) -> None:
        """Reset the rate limiter state."""
        self.request_times.clear()
        logger.debug("Rate limiter reset")
