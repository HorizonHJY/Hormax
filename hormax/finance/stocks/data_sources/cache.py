"""Data caching implementation for stock data.

This module provides caching functionality to reduce API calls
and improve performance.
"""

import hashlib
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from hormax.core.logging_setup import get_logger
from hormax.exceptions import CacheError
from hormax.finance.stocks.entities import StockData

logger = get_logger(__name__)


class DataCache:
    """Cache for stock data with TTL support.

    Attributes:
        cache_dir: Directory where cache files are stored.
        ttl_seconds: Time-to-live for cached data in seconds.
        enabled: Whether caching is enabled.
    """

    def __init__(
        self, cache_dir: str = ".cache/stock_data", ttl_seconds: int = 3600, enabled: bool = True
    ) -> None:
        """Initialize the data cache.

        Args:
            cache_dir: Directory for cache storage.
            ttl_seconds: Cache TTL in seconds.
            enabled: Whether caching is enabled.
        """
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_seconds
        self.enabled = enabled

        if self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Cache initialized at {self.cache_dir} with TTL={ttl_seconds}s")

    def _get_cache_key(self, ticker_symbol: str, start_date: str, end_date: str) -> str:
        """Generate a cache key for the given parameters.

        Args:
            ticker_symbol: Ticker symbol.
            start_date: Start date in ISO format.
            end_date: End date in ISO format.

        Returns:
            Cache key (hash).
        """
        key_str = f"{ticker_symbol}:{start_date}:{end_date}"
        return hashlib.sha256(key_str.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the file path for a cache key.

        Args:
            cache_key: The cache key.

        Returns:
            Path to the cache file.
        """
        return self.cache_dir / f"{cache_key}.pkl"

    def get(
        self, ticker_symbol: str, start_date: str, end_date: str
    ) -> Optional[StockData]:
        """Retrieve cached stock data if available and not expired.

        Args:
            ticker_symbol: Ticker symbol.
            start_date: Start date in ISO format.
            end_date: End date in ISO format.

        Returns:
            Cached StockData if available and valid, None otherwise.
        """
        if not self.enabled:
            return None

        try:
            cache_key = self._get_cache_key(ticker_symbol, start_date, end_date)
            cache_path = self._get_cache_path(cache_key)

            if not cache_path.exists():
                logger.debug(f"Cache miss for {ticker_symbol} ({start_date} to {end_date})")
                return None

            # Check if cache is expired
            file_mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
            age_seconds = (datetime.now() - file_mtime).total_seconds()

            if age_seconds > self.ttl_seconds:
                logger.debug(
                    f"Cache expired for {ticker_symbol} "
                    f"(age={age_seconds:.0f}s, TTL={self.ttl_seconds}s)"
                )
                cache_path.unlink()
                return None

            # Load cached data
            with open(cache_path, "rb") as f:
                stock_data = pickle.load(f)

            logger.info(
                f"Cache hit for {ticker_symbol} ({start_date} to {end_date}), "
                f"age={age_seconds:.0f}s"
            )
            return stock_data

        except Exception as e:
            logger.warning(f"Failed to retrieve from cache: {e}")
            return None

    def put(self, ticker_symbol: str, start_date: str, end_date: str, data: StockData) -> None:
        """Store stock data in the cache.

        Args:
            ticker_symbol: Ticker symbol.
            start_date: Start date in ISO format.
            end_date: End date in ISO format.
            data: StockData to cache.
        """
        if not self.enabled:
            return

        try:
            cache_key = self._get_cache_key(ticker_symbol, start_date, end_date)
            cache_path = self._get_cache_path(cache_key)

            with open(cache_path, "wb") as f:
                pickle.dump(data, f)

            logger.debug(f"Cached data for {ticker_symbol} ({start_date} to {end_date})")

        except Exception as e:
            logger.warning(f"Failed to write to cache: {e}")

    def clear(self) -> None:
        """Clear all cached data."""
        if not self.enabled:
            return

        try:
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()
            logger.info("Cache cleared")
        except Exception as e:
            raise CacheError(f"Failed to clear cache: {e}") from e

    def get_cache_size(self) -> int:
        """Get the number of cached items.

        Returns:
            Number of cache files.
        """
        if not self.enabled:
            return 0

        return len(list(self.cache_dir.glob("*.pkl")))
