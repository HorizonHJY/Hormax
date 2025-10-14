"""Custom exceptions for the Hormax package.

This module defines the exception hierarchy for the Hormax package,
enabling specific error handling and clear error messages.
"""


class HormaxError(Exception):
    """Base exception for all Hormax errors."""

    pass


class StockPackError(HormaxError):
    """Raised when stock pack generation fails."""

    pass


class FactorError(HormaxError):
    """Raised when factor calculation or registration fails."""

    pass


class ConfigError(HormaxError):
    """Raised when configuration is invalid or cannot be loaded."""

    pass


class ValidationError(HormaxError):
    """Raised when input validation fails."""

    pass


class StockDataError(HormaxError):
    """Raised when stock data fetching or processing fails."""

    pass


class RateLimitError(HormaxError):
    """Raised when rate limit is exceeded."""

    pass


class CacheError(HormaxError):
    """Raised when cache operations fail."""

    pass
