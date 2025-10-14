# Research: Finance Stocks Module - Technology Decisions

**Feature**: Finance Stocks Module - Stock Pack Builder & Modeling Framework
**Branch**: `001-en-as-the`
**Date**: 2025-10-14
**Purpose**: Resolve all technology choices and best practices for implementation

## Overview

This document records all technology decisions, evaluations, and best practices research conducted during Phase 0 planning. All decisions align with Hormax Constitution principles (modularity, type safety, YAML config, data responsibility).

## 1. Financial Data API Selection

### Decision: `yfinance` (primary), `alpha-vantage` (secondary option)

**Rationale**:
- **yfinance**: Free, no API key required, supports major global exchanges, well-maintained, excellent pandas integration
- **alpha-vantage**: Free tier available (5 API calls/minute), requires API key, good for users needing premium data

**Alternatives Considered**:
1. **pandas_datareader**: Deprecated for Yahoo Finance, unstable
2. **Quandl/NASDAQ Data Link**: Requires paid subscription for most datasets
3. **IEX Cloud**: Requires paid API key, limited free tier
4. **Raw Yahoo Finance API**: Undocumented, prone to breaking changes

**Rejected Because**: yfinance abstracts Yahoo Finance API instability and provides pandas DataFrame output directly. Alpha Vantage provides official API with documentation.

**Implementation Notes**:
- Use `yfinance.download()` for historical data (batch download supported)
- Use `yfinance.Ticker()` for metadata (company info, sector, exchange)
- Implement adapter pattern: `StockDataSource` abstracts provider, allowing swapping between yfinance/Alpha Vantage via config
- Example:
  ```python
  import yfinance as yf
  data = yf.download("AAPL", start="2024-01-01", end="2024-12-31")
  ticker = yf.Ticker("AAPL")
  info = ticker.info  # Dict with metadata
  ```

**Best Practices**:
- Always specify date ranges explicitly (don't rely on defaults)
- Handle timezone-aware dates (yfinance returns UTC)
- Validate ticker symbols before bulk download (check `ticker.info` for valid response)
- Use `auto_adjust=False` to get both `close` and `adj_close` columns

## 2. Excel Generation Library

### Decision: `openpyxl`

**Rationale**:
- **openpyxl**: Read/write XLSX, supports hyperlinks, cell formatting, multiple sheets, actively maintained
- Native Python (no external dependencies like LibreOffice)
- Compatible with Excel 2010+ and LibreOffice Calc

**Alternatives Considered**:
1. **xlsxwriter**: Write-only, faster for large files but cannot read existing files
2. **pandas.to_excel()**: Limited formatting options, no hyperlink support in older versions
3. **pyexcel**: Less popular, smaller community

**Rejected Because**: openpyxl provides complete read/write support with hyperlinks, styling, and formulas. xlsxwriter's write-only limitation is a dealbreaker for potential future features (editing existing packs).

**Implementation Notes**:
- Create workbook: `from openpyxl import Workbook; wb = Workbook()`
- Add sheet: `ws = wb.create_sheet("Sheet Name")`
- Add hyperlink:
  ```python
  from openpyxl.worksheet.hyperlink import Hyperlink
  ws["A1"].hyperlink = "https://example.com"
  ws["A1"].value = "Link Text"
  ws["A1"].style = "Hyperlink"  # Blue underlined text
  ```
- Save: `wb.save("output.xlsx")`

**Best Practices**:
- Use `openpyxl.styles` for consistent formatting (headers, data rows)
- Freeze top row for data sheets: `ws.freeze_panes = "A2"`
- Auto-adjust column widths based on content length
- Validate file size before writing (warn if >10MB)

## 3. Configuration & Validation

### Decision: `pydantic` v2 + `PyYAML`

**Rationale**:
- **pydantic**: Best-in-class data validation, auto-generates type-checked models from Python classes, excellent error messages
- **PyYAML**: Standard YAML parser for Python, safe_load prevents code injection

**Alternatives Considered**:
1. **marshmallow**: More verbose schema definitions, less IDE support
2. **cerberus**: Simpler but less powerful validation
3. **dataclasses + manual validation**: Error-prone, no automatic type coercion

**Rejected Because**: pydantic v2 offers superior performance (Rust core), automatic OpenAPI schema generation (future API feature), and seamless mypy integration.

**Implementation Notes**:
```python
from pydantic import BaseModel, Field, field_validator
import yaml

class DataSourceConfig(BaseModel):
    provider: str = Field(..., pattern="^(yfinance|alpha_vantage)$")
    api_key: str | None = None
    timeout: int = Field(default=30, gt=0, le=300)

    @field_validator("api_key")
    def validate_api_key(cls, v, info):
        if info.data.get("provider") == "alpha_vantage" and not v:
            raise ValueError("API key required for alpha_vantage provider")
        return v

# Load from YAML
with open("config.yaml") as f:
    raw = yaml.safe_load(f)
config = DataSourceConfig(**raw)  # Raises ValidationError if invalid
```

**Best Practices**:
- Use `Field()` for validation constraints (min/max, regex, custom validators)
- Enable strict mode: `pydantic.BaseModel.model_config["strict"] = True`
- Use environment variable integration: `pydantic_settings.BaseSettings` for env overrides
- Generate JSON schema for documentation: `config.model_json_schema()`

## 4. HTTP Caching

### Decision: `requests-cache`

**Rationale**:
- Drop-in replacement for `requests` library
- Supports multiple backends (SQLite, Redis, MongoDB, filesystem)
- Automatic TTL (time-to-live) management
- HTTP cache headers respected (`Cache-Control`, `Expires`)

**Alternatives Considered**:
1. **diskcache**: General-purpose cache, requires manual integration with requests
2. **cachetools**: In-memory only, lost on process restart
3. **Manual implementation**: Error-prone, reinventing the wheel

**Rejected Because**: requests-cache is purpose-built for HTTP caching with zero changes to request code (monkey-patches `requests` library).

**Implementation Notes**:
```python
import requests_cache

# Install cache (SQLite backend)
requests_cache.install_cache(
    "stock_data_cache",
    backend="sqlite",
    expire_after=3600,  # 1 hour TTL
    allowable_codes=[200],  # Only cache successful responses
    allowable_methods=["GET"],  # Only GET requests
)

# Use requests normally
response = requests.get("https://api.example.com/data")
print(response.from_cache)  # True if served from cache
```

**Best Practices**:
- Use SQLite backend for single-user CLI (filesystem for distributed systems)
- Set expire_after per request type (ticker metadata: 24h, price data: 1h)
- Clear cache on configuration changes: `requests_cache.clear()`
- Log cache hit/miss ratio for monitoring

## 5. Rate Limiting & Retries

### Decision: Custom implementation with exponential backoff

**Rationale**:
- No external library fully meets Hormax constitution requirements (logging, configurability)
- Simple to implement with `time.sleep()` and retry logic
- Full control over retry policies (transient vs permanent failures)

**Alternatives Considered**:
1. **ratelimit**: Decorator-based, but lacks retry logic
2. **tenacity**: Comprehensive retry library, but heavyweight for our needs
3. **backoff**: Decorator-based, less flexible for our logging requirements

**Rejected Because**: Custom implementation (100 lines) gives full control over logging, rate limit calculation, and error classification per constitution VII.

**Implementation Notes**:
```python
import time
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, requests_per_second: float = 5.0, max_retries: int = 3):
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = None
        self.max_retries = max_retries

    def wait_if_needed(self):
        if self.last_request_time:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                logger.debug(f"Rate limit: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
        self.last_request_time = time.time()

    def retry_with_backoff(self, func, *args, **kwargs):
        for attempt in range(self.max_retries):
            try:
                self.wait_if_needed()
                return func(*args, **kwargs)
            except (ConnectionError, TimeoutError) as e:
                if attempt == self.max_retries - 1:
                    raise
                wait_time = 2 ** attempt  # Exponential: 1s, 2s, 4s
                logger.warning(f"Retry {attempt+1}/{self.max_retries} after {wait_time}s: {e}")
                time.sleep(wait_time)
```

**Best Practices**:
- Classify errors: retry (network timeout, 5xx) vs no-retry (4xx, auth errors)
- Log all retries at WARNING level with context (attempt number, wait time, error)
- Make backoff multiplier configurable (default 2.0, range 1.5-3.0)
- Add jitter for distributed systems: `wait_time += random.uniform(0, 0.1 * wait_time)`

## 6. Returns Calculation

### Decision: pandas vectorized operations

**Rationale**:
- pandas Series operations are vectorized (C-optimized), 100x faster than Python loops
- Built-in support for missing data (NaN handling with `fillna`, `dropna`)
- Chaining operations for readability: `prices.pct_change().fillna(0)`

**Alternatives Considered**:
1. **numpy arrays**: Faster but loses date indexing
2. **Manual loops**: 100x slower, error-prone
3. **TA-Lib**: Overkill for simple returns, adds heavy dependency

**Rejected Because**: pandas provides perfect balance of performance, readability, and date handling.

**Implementation Notes**:
```python
import pandas as pd
import numpy as np

# Simple return: (P_t - P_t-1) / P_t-1
simple_returns = prices.pct_change()

# Log return: ln(P_t / P_t-1)
log_returns = np.log(prices / prices.shift(1))

# Validation
assert not np.isinf(simple_returns).any(), "Infinite returns detected"
assert simple_returns.between(-1.0, 10.0).all(), "Extreme returns detected (check data quality)"
```

**Best Practices**:
- Always validate returns for inf, extreme values (>1000% daily return = data error)
- Handle first row NaN (no prior price): `returns.fillna(0)` or `returns.iloc[0] = 0`
- Use `Decimal` for high-precision financial calculations (Python `float` has rounding errors)
- Log returns preferred for aggregating multi-period returns (additive property)

## 7. Data Quality & Gap Handling

### Decision: Forward fill for missing dates, log gaps >7 days

**Rationale**:
- Weekends/holidays: normal gaps, forward fill last known price
- Extended gaps (>7 days): unusual, may indicate delisting or data issue, log warning
- Transparency: never silently drop data, always log imputation

**Alternatives Considered**:
1. **Drop rows with missing data**: Loses information, breaks date continuity
2. **Interpolate linearly**: Invents prices that didn't exist (misleading)
3. **Backward fill**: Uses future information (look-ahead bias)

**Rejected Because**: Forward fill preserves last known state without inventing data or introducing bias. Logging long gaps alerts users to data quality issues.

**Implementation Notes**:
```python
def fill_missing_dates(df: pd.DataFrame, start_date, end_date) -> pd.DataFrame:
    # Create full date range (business days only for stocks)
    all_dates = pd.bdate_range(start=start_date, end=end_date)
    df = df.set_index("date").reindex(all_dates)

    # Detect gaps >7 days
    gaps = df[df.isna().any(axis=1)]
    if len(gaps) > 0:
        logger.warning(f"Data gaps detected: {gaps.index.tolist()}")

    # Forward fill
    df = df.ffill()
    return df.reset_index()
```

**Best Practices**:
- Use `pd.bdate_range()` for business days (excludes weekends)
- Consider exchange-specific holidays (NYSE calendar via `pandas_market_calendars`)
- Flag imputed values in metadata sheet ("Data Imputation" column)
- Allow users to configure fill strategy via config (forward/backward/interpolate/drop)

## 8. Testing Strategy

### Decision: pytest with `pytest-mock`, `freezegun`, `vcr.py`

**Rationale**:
- **pytest**: Standard Python testing framework (per constitution V)
- **pytest-mock**: Clean mocking syntax for external APIs
- **freezegun**: Mock datetime for reproducible tests
- **vcr.py**: Record/replay HTTP interactions (integration tests without live API)

**Alternatives Considered**:
1. **unittest**: More verbose, less powerful fixtures
2. **nose2**: Deprecated
3. **responses**: HTTP mocking, but requires manual recording (vcr.py auto-records)

**Rejected Because**: pytest + plugins ecosystem provides best developer experience and aligns with constitution.

**Implementation Notes**:
```python
import pytest
from freezegun import freeze_time
import vcr

# Unit test (mocked API)
def test_fetch_price_history(mocker):
    mock_yfinance = mocker.patch("yfinance.download")
    mock_yfinance.return_value = pd.DataFrame({"close": [100, 101, 102]})

    source = StockDataSource()
    df = source.fetch_price_history(Ticker("AAPL"), date(2024,1,1), date(2024,1,3))
    assert len(df) == 3

# Integration test (recorded HTTP)
@vcr.use_cassette("tests/fixtures/vcr_cassettes/aapl_2024.yaml")
def test_fetch_real_data():
    source = StockDataSource()
    df = source.fetch_price_history(Ticker("AAPL"), date(2024,1,1), date(2024,12,31))
    assert not df.empty

# Time-sensitive test (frozen time)
@freeze_time("2024-10-14 12:00:00")
def test_date_validation():
    with pytest.raises(ValueError, match="future"):
        DateRange(date(2024,10,1), date(2025,1,1))  # Future end date
```

**Best Practices**:
- Organize tests: `tests/unit/`, `tests/integration/`, `tests/fixtures/`
- Use `@pytest.fixture` for common setup (sample tickers, date ranges, config)
- Record VCR cassettes once, commit to repo (tests run without network)
- Update cassettes monthly (delete and re-record to ensure API compatibility)

## 9. Logging Setup

### Decision: Python `logging` with structured context via `LoggerAdapter`

**Rationale**:
- Standard library (no external deps)
- Supports multiple handlers (console + file)
- LoggerAdapter injects context (ticker, factor) into every log message

**Alternatives Considered**:
1. **structlog**: More powerful structured logging, but adds dependency
2. **loguru**: Simpler API, but non-standard (harder for users familiar with logging)
3. **print statements**: Violates constitution III

**Rejected Because**: Standard `logging` meets all requirements with LoggerAdapter for context injection.

**Implementation Notes**:
```python
import logging
from logging.handlers import RotatingFileHandler

def setup_logging(config: dict) -> logging.Logger:
    logger = logging.getLogger("hormax.finance.stocks")
    logger.setLevel(config["logging"]["level"])

    # Console handler (INFO+)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))

    # File handler (DEBUG+, rotating)
    file_handler = RotatingFileHandler(
        config["logging"]["file"],
        maxBytes=10_000_000,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(ticker)s] - %(message)s"
    ))

    logger.addHandler(console)
    logger.addHandler(file_handler)
    return logger

# Usage with context
logger = setup_logging(config)
ticker_logger = logging.LoggerAdapter(logger, {"ticker": "AAPL"})
ticker_logger.info("Fetching price history")
# Output: 2025-10-14 10:15:32 - hormax.finance.stocks - INFO - [AAPL] - Fetching price history
```

**Best Practices**:
- Use logger hierarchy: `hormax` (root) → `hormax.finance` → `hormax.finance.stocks`
- Never log sensitive data (API keys): mask in logs (`api_key[:4]+"****"`)
- Log timing for performance analysis: `@log_execution_time` decorator
- Use `logger.exception()` in except blocks (includes traceback)

## 10. Custom Exceptions Design

### Decision: Exception hierarchy in `hormax/exceptions.py`

**Rationale**:
- Centralized exception definitions (per constitution III)
- Hierarchy enables granular error handling
- Actionable error messages with context

**Exception Hierarchy**:
```python
# hormax/exceptions.py

class HormaxError(Exception):
    """Base exception for all Hormax errors."""
    pass

# Stock Pack Errors
class StockPackError(HormaxError):
    """Base error for stock pack operations."""
    pass

class StockDataError(StockPackError):
    """Error fetching stock data from API."""
    def __init__(self, ticker: str, message: str):
        self.ticker = ticker
        super().__init__(f"[{ticker}] {message}")

class ValidationError(StockPackError):
    """Input validation error."""
    pass

# Factor Modeling Errors
class FactorError(HormaxError):
    """Base error for factor modeling."""
    pass

class FactorRegistrationError(FactorError):
    """Error registering factor."""
    pass

class FactorCalculationError(FactorError):
    """Error calculating factor score."""
    def __init__(self, ticker: str, factor_name: str, message: str):
        self.ticker = ticker
        self.factor_name = factor_name
        super().__init__(f"[{ticker} + {factor_name}] {message}")

# Config Errors
class ConfigError(HormaxError):
    """Configuration file error."""
    pass
```

**Best Practices**:
- Include actionable context in error messages (ticker, date range, factor name)
- Suggest remediation: `raise ValidationError("Invalid ticker 'XYZ'. Check symbol exists.")`
- Use specific exceptions for specific errors (avoid bare `Exception`)
- Document exceptions in docstrings: `Raises: StockDataError: If API returns non-200 status`

## Summary of Key Decisions

| Component | Technology | Reason |
|-----------|-----------|--------|
| Data Source | yfinance (primary), alpha-vantage (secondary) | Free, pandas integration, no API key for yfinance |
| Excel Generation | openpyxl | Hyperlink support, read/write, active maintenance |
| Config Validation | pydantic v2 + PyYAML | Best-in-class validation, type safety, error messages |
| HTTP Caching | requests-cache | Drop-in replacement, automatic TTL, multiple backends |
| Rate Limiting | Custom implementation | Full control, logging, constitution compliance |
| Returns Calculation | pandas vectorized operations | Performance, date handling, NaN support |
| Gap Handling | Forward fill + logging | Transparency, no invented data, alerts on long gaps |
| Testing | pytest + pytest-mock + freezegun + vcr.py | Constitution-aligned, best DX, record/replay HTTP |
| Logging | Python logging + LoggerAdapter | Standard library, structured context injection |
| Exceptions | Custom hierarchy in hormax/exceptions.py | Centralized, actionable, granular error handling |

All decisions align with Hormax Constitution principles (modularity, type safety, YAML config, data responsibility, testing discipline).
