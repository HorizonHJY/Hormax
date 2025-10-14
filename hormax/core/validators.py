"""Input validation utilities for stock pack operations.

This module provides validation functions for tickers, date ranges,
and other inputs to ensure data quality and early error detection.
"""

from datetime import date, datetime
from typing import List

from hormax.exceptions import ValidationError
from hormax.finance.stocks.entities import DateRange, Ticker


def validate_ticker_symbol(symbol: str) -> None:
    """Validate a ticker symbol.

    Args:
        symbol: The ticker symbol to validate.

    Raises:
        ValidationError: If the ticker symbol is invalid.
    """
    if not symbol or not symbol.strip():
        raise ValidationError("Ticker symbol cannot be empty")

    if len(symbol) > 10:
        raise ValidationError(f"Ticker symbol '{symbol}' exceeds 10 characters")

    if not symbol.replace(".", "").replace("-", "").isalnum():
        raise ValidationError(
            f"Ticker symbol '{symbol}' contains invalid characters. "
            "Only alphanumeric characters, dots, and hyphens are allowed."
        )


def validate_tickers(tickers: List[str]) -> List[Ticker]:
    """Validate a list of ticker symbols and convert to Ticker objects.

    Args:
        tickers: List of ticker symbols as strings.

    Returns:
        List of validated Ticker objects.

    Raises:
        ValidationError: If any ticker is invalid or the list is empty.
    """
    if not tickers:
        raise ValidationError("Ticker list cannot be empty")

    if len(tickers) > 100:
        raise ValidationError(
            f"Ticker list contains {len(tickers)} symbols. Maximum allowed is 100."
        )

    validated_tickers = []
    seen = set()

    for symbol in tickers:
        symbol = symbol.strip().upper()

        if symbol in seen:
            raise ValidationError(f"Duplicate ticker symbol: {symbol}")

        validate_ticker_symbol(symbol)
        validated_tickers.append(Ticker(symbol=symbol))
        seen.add(symbol)

    return validated_tickers


def validate_date_range(start: date, end: date) -> DateRange:
    """Validate a date range.

    Args:
        start: Start date (inclusive).
        end: End date (inclusive).

    Returns:
        Validated DateRange object.

    Raises:
        ValidationError: If the date range is invalid.
    """
    if start > end:
        raise ValidationError(f"Start date {start} must be <= end date {end}")

    if end > date.today():
        raise ValidationError(f"End date {end} cannot be in the future")

    # Check for reasonable date range (not too far in the past)
    min_date = date(1990, 1, 1)
    if start < min_date:
        raise ValidationError(f"Start date {start} is before {min_date}")

    # Check for maximum range (10 years)
    days_diff = (end - start).days
    if days_diff > 3650:  # ~10 years
        raise ValidationError(
            f"Date range is {days_diff} days. Maximum allowed is 3650 days (10 years)."
        )

    return DateRange(start=start, end=end)


def validate_date_string(date_str: str, param_name: str = "date") -> date:
    """Validate and parse a date string in ISO format (YYYY-MM-DD).

    Args:
        date_str: Date string to validate.
        param_name: Parameter name for error messages.

    Returns:
        Parsed date object.

    Raises:
        ValidationError: If the date string is invalid.
    """
    try:
        parsed = datetime.strptime(date_str, "%Y-%m-%d").date()
        return parsed
    except ValueError as e:
        raise ValidationError(
            f"Invalid {param_name} format: '{date_str}'. Expected YYYY-MM-DD."
        ) from e
