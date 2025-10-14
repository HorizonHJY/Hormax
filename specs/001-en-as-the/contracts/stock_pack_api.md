# API Contract: Stock Pack Builder

**Feature**: Finance Stocks Module - Stock Pack Builder
**Date**: 2025-10-14
**Purpose**: Define public API interfaces for stock pack generation and factor modeling

## Overview

This document defines the public API contracts for the stock pack builder and factor modeling system. These are Python library interfaces (not REST APIs), but follow similar contract principles: clear inputs/outputs, error conditions, and backward compatibility guarantees.

## Stock Pack Builder API

### 1. `build_stock_pack()`

**Purpose**: Generate a complete stock pack (Excel file with data, returns, metadata)

**Signature**:
```python
def build_stock_pack(
    tickers: list[str],
    start_date: str | date,
    end_date: str | date,
    output_path: str,
    config: dict | None = None
) -> StockPack:
    """
    Generate stock pack for given tickers and date range.

    Args:
        tickers: List of stock ticker symbols (e.g., ["AAPL", "MSFT"])
        start_date: Start date (ISO format "YYYY-MM-DD" or date object)
        end_date: End date (ISO format "YYYY-MM-DD" or date object)
        output_path: Path for output Excel file (must end with .xlsx)
        config: Optional config dict (overrides default config)

    Returns:
        StockPack object with metadata

    Raises:
        ValidationError: If inputs invalid (empty tickers, bad date range, invalid path)
        StockDataError: If API fetch fails for all tickers
        ConfigError: If config invalid

    Examples:
        >>> from hormax.finance.stocks import build_stock_pack
        >>> from datetime import date
        >>> pack = build_stock_pack(
        ...     tickers=["AAPL", "MSFT", "GOOGL"],
        ...     start_date="2024-01-01",
        ...     end_date="2024-12-31",
        ...     output_path="my_stock_pack.xlsx"
        ... )
        >>> print(pack.excel_file_path)
        "my_stock_pack.xlsx"
        >>> print(pack.success_rate())
        1.0  # 100% success
    """
```

**Input Validation**:
- `tickers`: Non-empty list, each symbol 1-5 chars, alphanumeric
- `start_date` / `end_date`: Valid dates, start <= end, not in future
- `output_path`: Valid file path, ends with .xlsx
- `config`: If provided, must match StockPackConfig schema

**Output Contract**:
- Returns `StockPack` object (never None)
- `StockPack.excel_file_path` points to valid Excel file
- Excel file contains minimum 3 sheets:
  1. Field Dictionary (field name, type, description, source URL)
  2. Returns (ticker, date, price, simple_return, log_return)
  3. Metadata & Logs (generation time, input params, errors/warnings)

**Error Handling**:
- If ALL tickers fail: raise `StockDataError`
- If SOME tickers fail: continue, log failures, return partial results
- If config invalid: raise `ConfigError` before processing
- If output path unwritable: raise `IOError` at save time

**Performance SLA**:
- 10 tickers, 1-year range: <60 seconds (excluding API latency)
- Progress logged at INFO level (per-ticker fetch completion)

---

### 2. `validate_tickers()`

**Purpose**: Validate ticker symbols before processing

**Signature**:
```python
def validate_tickers(tickers: list[str]) -> dict[str, bool]:
    """
    Validate list of ticker symbols.

    Args:
        tickers: List of ticker symbols to validate

    Returns:
        Dict mapping ticker → is_valid (bool)

    Examples:
        >>> validate_tickers(["AAPL", "INVALID", "MSFT"])
        {"AAPL": True, "INVALID": False, "MSFT": True}
    """
```

**Output Contract**:
- Returns dict with entry for each input ticker
- `True` means ticker exists and is fetchable
- `False` means ticker not found or API error

---

### 3. `load_config()`

**Purpose**: Load and validate configuration from YAML file

**Signature**:
```python
def load_config(config_path: str | Path) -> StockPackConfig:
    """
    Load configuration from YAML file with validation.

    Args:
        config_path: Path to YAML config file

    Returns:
        Validated StockPackConfig object

    Raises:
        ConfigError: If file not found, invalid YAML, or schema validation fails

    Examples:
        >>> config = load_config("config/stock_pack.yaml")
        >>> print(config.data_source.provider)
        "yfinance"
    """
```

**Input Validation**:
- File must exist and be readable
- Must be valid YAML syntax
- Must match StockPackConfig schema (pydantic validation)

**Error Messages**:
- File not found: `ConfigError: Config file not found: {path}`
- Invalid YAML: `ConfigError: Invalid YAML syntax: {error}`
- Schema validation: `ConfigError: Invalid config: data_source.provider must be 'yfinance' or 'alpha_vantage'`

---

## Factor Modeling API

### 4. `register_factor()`

**Purpose**: Register a factor in the global registry

**Signature**:
```python
def register_factor(factor: FactorInterface) -> None:
    """
    Register factor for use in calculations.

    Args:
        factor: Factor instance implementing FactorInterface

    Raises:
        FactorRegistrationError: If factor invalid or name collision

    Examples:
        >>> class MomentumFactor(FactorInterface):
        ...     @property
        ...     def name(self) -> str:
        ...         return "momentum_30d"
        ...     def calculate(self, data: pd.DataFrame) -> float:
        ...         return data["close"].pct_change(30).iloc[-1]
        ...     def get_requirements(self) -> list[str]:
        ...         return ["price_history"]
        >>> register_factor(MomentumFactor())
    """
```

**Input Validation**:
- `factor` must implement all FactorInterface methods
- `factor.name` must be unique (not already registered)
- `factor.get_requirements()` must return list of strings

**Error Conditions**:
- Missing method: `FactorRegistrationError: Factor must implement calculate() method`
- Name collision: `FactorRegistrationError: Factor 'momentum' already registered`
- Invalid requirements: `FactorRegistrationError: Requirements must be list of strings`

---

### 5. `calculate_factors()`

**Purpose**: Calculate factor scores for tickers

**Signature**:
```python
def calculate_factors(
    tickers: list[str],
    factors: list[str],
    date_range: tuple[str | date, str | date],
    error_policy: str = "skip",
    config: dict | None = None
) -> pd.DataFrame:
    """
    Calculate factor scores for tickers.

    Args:
        tickers: List of ticker symbols
        factors: List of factor names (must be registered)
        date_range: (start_date, end_date) for data fetch
        error_policy: "skip", "log", or "fail"
        config: Optional config override

    Returns:
        DataFrame with columns: ticker, factor, score, timestamp, metadata

    Raises:
        FactorError: If factor not registered
        FactorCalculationError: If error_policy="fail" and calculation fails
        ValidationError: If inputs invalid

    Examples:
        >>> df = calculate_factors(
        ...     tickers=["AAPL", "MSFT"],
        ...     factors=["momentum_30d", "volatility"],
        ...     date_range=("2024-01-01", "2024-12-31"),
        ...     error_policy="skip"
        ... )
        >>> print(df)
           ticker        factor     score           timestamp
        0   AAPL  momentum_30d      0.05 2025-10-14 10:00:00
        1   AAPL    volatility      0.23 2025-10-14 10:00:00
        2   MSFT  momentum_30d      0.03 2025-10-14 10:00:00
        3   MSFT    volatility      0.18 2025-10-14 10:00:00
    """
```

**Input Validation**:
- `tickers`: Non-empty list of valid symbols
- `factors`: Non-empty list, all factors must be registered
- `date_range`: Valid dates, start <= end
- `error_policy`: Must be "skip", "log", or "fail"

**Output Contract**:
- Returns DataFrame (never None, but may be empty if all calculations fail)
- Columns: `ticker` (str), `factor` (str), `score` (float), `timestamp` (datetime), `metadata` (dict)
- One row per successful ticker-factor calculation

**Error Handling**:
- Factor not registered: raise `FactorError` immediately
- Calculation fails with `error_policy="skip"`: log warning, omit row
- Calculation fails with `error_policy="log"`: log error, include row with score=NaN
- Calculation fails with `error_policy="fail"`: raise `FactorCalculationError`

---

## CLI Interface (Optional)

### 6. Command: `hormax stocks build`

**Purpose**: CLI wrapper for `build_stock_pack()`

**Usage**:
```bash
hormax stocks build \
  --tickers AAPL MSFT GOOGL \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --output my_pack.xlsx \
  --config config/stock_pack.yaml
```

**Arguments**:
| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--tickers` | Yes | - | Space-separated ticker symbols |
| `--start` | Yes | - | Start date (YYYY-MM-DD) |
| `--end` | Yes | - | End date (YYYY-MM-DD) |
| `--output` | Yes | - | Output Excel file path |
| `--config` | No | `config/stock_pack.yaml` | Config file path |

**Output**:
- Prints progress to stdout (INFO level logs)
- Prints summary on completion:
  ```
  Stock pack generated successfully!
  Tickers: AAPL, MSFT, GOOGL (3 total, 3 successful)
  Date range: 2024-01-01 to 2024-12-31
  Output: my_pack.xlsx
  Generation time: 45.2 seconds
  ```

**Exit Codes**:
- `0`: Success
- `1`: Validation error (bad inputs)
- `2`: Data error (all tickers failed)
- `3`: Config error (invalid config file)

---

### 7. Command: `hormax stocks factors`

**Purpose**: CLI wrapper for `calculate_factors()`

**Usage**:
```bash
hormax stocks factors \
  --tickers AAPL MSFT \
  --factors momentum_30d volatility \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --output factors.csv \
  --error-policy skip
```

**Arguments**:
| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--tickers` | Yes | - | Space-separated ticker symbols |
| `--factors` | Yes | - | Space-separated factor names |
| `--start` | Yes | - | Start date (YYYY-MM-DD) |
| `--end` | Yes | - | End date (YYYY-MM-DD) |
| `--output` | Yes | - | Output file (CSV/JSON) |
| `--error-policy` | No | `skip` | Error policy (skip/log/fail) |

**Output**:
- CSV or JSON file with factor scores
- Prints summary to stdout

---

## Versioning & Backward Compatibility

**Current Version**: 1.0.0 (initial release)

**Semantic Versioning**:
- MAJOR (1.x.x → 2.x.x): Breaking API changes (function signatures, removed functions)
- MINOR (x.1.x → x.2.x): New features (new functions, new parameters with defaults)
- PATCH (x.x.1 → x.x.2): Bug fixes, internal refactoring (no API changes)

**Backward Compatibility Guarantees**:
1. Function signatures will not change within MAJOR version
2. New optional parameters may be added (with defaults) in MINOR versions
3. Return types will not change within MAJOR version
4. Exceptions raised will not change (new exceptions may be added)
5. Config schema will not remove required fields within MAJOR version

**Deprecation Policy**:
- Deprecated functions: Warned for 1 MINOR version, removed in next MAJOR
- Example: Deprecated in 1.5.0, removed in 2.0.0

**Breaking Changes** (require MAJOR version bump):
- Remove function
- Change function signature (except adding optional params)
- Change return type
- Remove config field
- Rename exception class

**Non-Breaking Changes** (MINOR/PATCH version bump):
- Add new function
- Add optional parameter with default
- Add new config field (with default)
- Add new exception class
- Internal refactoring

## Error Response Format

All exceptions include:
- **Message**: Human-readable error description
- **Context**: Relevant context (ticker, date, factor name)
- **Suggestion**: Actionable remediation (where applicable)

**Example**:
```python
try:
    pack = build_stock_pack(...)
except StockDataError as e:
    print(e)
    # Output: [AAPL] Failed to fetch stock data: API returned 404 Not Found. Check ticker symbol is valid.
    print(e.ticker)  # "AAPL"
    print(e.__cause__)  # Original exception (requests.HTTPError)
```

## Testing Contract

All public API functions must have:
1. **Unit tests**: With mocked external dependencies (API, file system)
2. **Integration tests**: With real API calls (using VCR for recording)
3. **Examples**: In docstrings (must be valid and tested)

**Test Coverage Target**: 85% minimum for new code

---

This API contract serves as the interface specification for the Finance Stocks Module. Implementation details may vary, but this contract must remain stable within MAJOR versions.
