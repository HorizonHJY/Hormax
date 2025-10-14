"""Configuration management using Pydantic v2.

This module provides configuration loading and validation for the Hormax package.
Configuration is loaded from YAML files with environment variable overrides.
"""

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, field_validator

from hormax.exceptions import ConfigError


class DataSourceConfig(BaseModel):
    """Data source configuration.

    Attributes:
        provider: Data provider name ('yfinance' or 'alpha_vantage').
        api_key: Optional API key (can be set via HORMAX_DATA_SOURCE_API_KEY).
        timeout: Request timeout in seconds.
    """

    provider: str = Field(default="yfinance", pattern="^(yfinance|alpha_vantage)$")
    api_key: Optional[str] = None
    timeout: int = Field(default=30, gt=0, le=300)

    @field_validator("api_key", mode="before")
    @classmethod
    def load_from_env(cls, v: Optional[str]) -> Optional[str]:
        """Load API key from environment if not provided."""
        if v is None:
            return os.getenv("HORMAX_DATA_SOURCE_API_KEY")
        return v


class CacheConfig(BaseModel):
    """Cache configuration.

    Attributes:
        enabled: Whether caching is enabled.
        directory: Cache directory path.
        ttl_seconds: Time-to-live for cached data in seconds.
    """

    enabled: bool = True
    directory: str = ".cache/stock_data"
    ttl_seconds: int = Field(default=3600, gt=0)


class RateLimitConfig(BaseModel):
    """Rate limiting configuration.

    Attributes:
        requests_per_second: Maximum requests per second.
        max_retries: Maximum number of retry attempts.
    """

    requests_per_second: float = Field(default=5.0, gt=0, le=100)
    max_retries: int = Field(default=3, ge=0, le=10)


class LoggingConfig(BaseModel):
    """Logging configuration.

    Attributes:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        format: Log message format string.
        file: Optional log file path.
    """

    level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = "logs/stock_pack.log"


class StockPackConfig(BaseModel):
    """Complete stock pack configuration.

    Attributes:
        data_source: Data source configuration.
        cache: Cache configuration.
        rate_limit: Rate limiting configuration.
        logging: Logging configuration.
    """

    data_source: DataSourceConfig = Field(default_factory=DataSourceConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


class ConfigLoader:
    """Configuration loader with YAML and environment variable support."""

    @staticmethod
    def load_from_yaml(config_path: Path) -> StockPackConfig:
        """Load configuration from a YAML file.

        Args:
            config_path: Path to the YAML configuration file.

        Returns:
            Validated StockPackConfig instance.

        Raises:
            ConfigError: If the file cannot be read or validation fails.
        """
        try:
            if not config_path.exists():
                raise ConfigError(f"Configuration file not found: {config_path}")

            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if data is None:
                data = {}

            return StockPackConfig(**data)

        except yaml.YAMLError as e:
            raise ConfigError(f"Failed to parse YAML configuration: {e}") from e
        except Exception as e:
            raise ConfigError(f"Failed to load configuration: {e}") from e

    @staticmethod
    def load_default() -> StockPackConfig:
        """Load default configuration.

        Returns:
            StockPackConfig with default values and environment variable overrides.
        """
        return StockPackConfig()

    @staticmethod
    def load(config_path: Optional[Path] = None) -> StockPackConfig:
        """Load configuration from file or use defaults.

        Args:
            config_path: Optional path to YAML configuration file.

        Returns:
            Validated StockPackConfig instance.
        """
        if config_path is None:
            # Try to find config in default locations
            default_paths = [
                Path("config/stock_pack.yaml"),
                Path("stock_pack.yaml"),
                Path.home() / ".hormax" / "stock_pack.yaml",
            ]

            for path in default_paths:
                if path.exists():
                    config_path = path
                    break

        if config_path and config_path.exists():
            return ConfigLoader.load_from_yaml(config_path)

        return ConfigLoader.load_default()
