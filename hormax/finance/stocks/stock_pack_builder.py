"""Stock pack builder orchestration.

This module provides the main orchestration for building stock data packs,
coordinating data fetching, processing, and Excel generation.
"""

from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

from hormax.core.config import ConfigLoader, StockPackConfig
from hormax.core.logging_setup import get_logger, setup_logging
from hormax.core.validators import validate_date_range, validate_tickers
from hormax.exceptions import StockPackError
from hormax.finance.stocks.builders.excel_builder import ExcelBuilder
from hormax.finance.stocks.data_sources.cache import DataCache
from hormax.finance.stocks.data_sources.rate_limiter import RateLimiter
from hormax.finance.stocks.data_sources.stock_data_source import StockDataSource
from hormax.finance.stocks.entities import DateRange, StockData, StockPack, Ticker
from hormax.finance.stocks.processors.data_cleaner import DataCleaner
from hormax.finance.stocks.processors.returns_calculator import ReturnsCalculator

logger = get_logger(__name__)


class StockPackBuilder:
    """Orchestrator for building stock data packs.

    This class coordinates the entire process of:
    1. Fetching stock data from sources
    2. Cleaning and validating data
    3. Calculating returns and metrics
    4. Generating Excel output

    Attributes:
        config: Configuration for the stock pack builder.
        data_source: Data source for fetching stock data.
        cache: Cache for stock data.
        rate_limiter: Rate limiter for API calls.
        data_cleaner: Data cleaner for preprocessing.
        returns_calculator: Returns calculator.
        excel_builder: Excel workbook builder.
    """

    def __init__(self, config: Optional[StockPackConfig] = None) -> None:
        """Initialize the stock pack builder.

        Args:
            config: Optional configuration. If None, loads default config.
        """
        # Load config
        self.config = config if config is not None else ConfigLoader.load_default()

        # Setup logging
        setup_logging(self.config.logging)

        # Initialize components
        self.data_source = StockDataSource(timeout=self.config.data_source.timeout)
        self.cache = DataCache(
            cache_dir=self.config.cache.directory,
            ttl_seconds=self.config.cache.ttl_seconds,
            enabled=self.config.cache.enabled,
        )
        self.rate_limiter = RateLimiter(
            requests_per_second=self.config.rate_limit.requests_per_second,
            max_retries=self.config.rate_limit.max_retries,
        )
        self.data_cleaner = DataCleaner()
        self.returns_calculator = ReturnsCalculator()
        self.excel_builder = ExcelBuilder()

        logger.info("StockPackBuilder initialized")

    def build_pack(
        self,
        tickers: List[str],
        start_date: date,
        end_date: date,
        output_path: Path,
    ) -> StockPack:
        """Build a complete stock data pack.

        Args:
            tickers: List of ticker symbols.
            start_date: Start date for data (inclusive).
            end_date: End date for data (inclusive).
            output_path: Path for output Excel file.

        Returns:
            StockPack containing all data and metadata.

        Raises:
            StockPackError: If pack building fails.
        """
        try:
            start_time = datetime.now()
            logger.info(
                f"Building stock pack for {len(tickers)} tickers "
                f"from {start_date} to {end_date}"
            )

            # Validate inputs
            validated_tickers = validate_tickers(tickers)
            date_range = validate_date_range(start_date, end_date)

            # Fetch and process data for each ticker
            stock_data_map: Dict[str, StockData] = {}
            returns_map = {}

            for ticker in validated_tickers:
                logger.info(f"Processing {ticker.symbol}...")

                # Fetch data (with caching and rate limiting)
                stock_data = self._fetch_stock_data(ticker, start_date, end_date)

                # Clean data
                cleaned_data = self.data_cleaner.clean_stock_data(stock_data)

                # Calculate returns
                returns = self.returns_calculator.calculate_returns(cleaned_data)

                # Store results
                stock_data_map[ticker.symbol] = cleaned_data
                returns_map[ticker.symbol] = returns

            # Create stock pack
            stock_pack = StockPack(
                tickers=validated_tickers,
                date_range=date_range,
                stock_data=stock_data_map,
                returns=returns_map,
                metadata={
                    "builder_version": "0.1.0",
                    "data_provider": self.config.data_source.provider,
                    "build_duration_seconds": (datetime.now() - start_time).total_seconds(),
                },
            )

            # Generate Excel output
            self.excel_builder.build_workbook(stock_pack, output_path)

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"Stock pack built successfully in {elapsed:.1f}s, saved to {output_path}"
            )

            return stock_pack

        except Exception as e:
            logger.error(f"Failed to build stock pack: {e}")
            raise StockPackError(f"Failed to build stock pack: {e}") from e

    def _fetch_stock_data(self, ticker: Ticker, start_date: date, end_date: date) -> StockData:
        """Fetch stock data with caching and rate limiting.

        Args:
            ticker: Ticker to fetch.
            start_date: Start date.
            end_date: End date.

        Returns:
            StockData for the ticker.
        """
        # Check cache first
        cached_data = self.cache.get(
            ticker.symbol, start_date.isoformat(), end_date.isoformat()
        )

        if cached_data is not None:
            return cached_data

        # Fetch from source with rate limiting
        def fetch() -> StockData:
            return self.data_source.fetch_price_history(ticker, start_date, end_date)

        stock_data = self.rate_limiter.execute_with_retry(fetch)

        # Cache the result
        self.cache.put(ticker.symbol, start_date.isoformat(), end_date.isoformat(), stock_data)

        return stock_data


def build_stock_pack(
    tickers: List[str],
    start_date: date,
    end_date: date,
    output_path: Path,
    config_path: Optional[Path] = None,
) -> StockPack:
    """Convenience function to build a stock pack.

    Args:
        tickers: List of ticker symbols.
        start_date: Start date for data (inclusive).
        end_date: End date for data (inclusive).
        output_path: Path for output Excel file.
        config_path: Optional path to configuration file.

    Returns:
        StockPack containing all data and metadata.

    Raises:
        StockPackError: If pack building fails.
    """
    config = ConfigLoader.load(config_path) if config_path else None
    builder = StockPackBuilder(config)
    return builder.build_pack(tickers, start_date, end_date, output_path)
