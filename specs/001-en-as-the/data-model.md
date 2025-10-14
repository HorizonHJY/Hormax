# Data Model: Finance Stocks Module

**Feature**: Finance Stocks Module - Stock Pack Builder & Modeling Framework
**Branch**: `001-en-as-the`
**Date**: 2025-10-14
**Purpose**: Define all entities, their attributes, relationships, validation rules, and state transitions

## Overview

This data model defines all entities used in the stock pack builder and factor modeling system. Entities are implemented as Python dataclasses (for immutability and type safety) or pydantic models (for validation), following Hormax Constitution principles II (Type Safety) and IV (Module Organization).

## Entity Diagram

```
┌────────────────┐
│     Ticker     │──────┐
│                │      │
│ - symbol: str  │      │ Many tickers
│ - name: str?   │      │ in one pack
│ - exchange     │      │
│ - sector       │      │
│ - is_active    │      │
└────────────────┘      │
         │              │
         │ Has          ▼
         │        ┌──────────────┐
         │        │  StockPack   │
         │        │              │
         ▼        │ - tickers    │
┌────────────────┐│ - date_range │
│   StockData    ││ - timestamp  │
│                ││ - file_path  │
│ - ticker       ││ - metadata   │
│ - date         │└──────────────┘
│ - OHLCV        │       │
│ - adj_close    │       │ Contains
└────────────────┘       │
         │               ▼
         │ Derives ┌──────────────┐
         │         │  DateRange   │
         ▼         │              │
┌────────────────┐│ - start_date │
│    Returns     ││ - end_date   │
│                │└──────────────┘
│ - ticker       │
│ - date         │
│ - simple_ret   │
│ - log_ret      │
│ - period       │
└────────────────┘

     Factor System

┌────────────────┐      ┌──────────────────┐
│     Factor     │◄─────│  FactorRegistry  │
│  (Interface)   │      │                  │
│                │      │ - factors: dict  │
│ - name         │      │ + register()     │
│ - calculate()  │      │ + get_factor()   │
│ - get_req()    │      │ + validate()     │
└────────────────┘      └──────────────────┘
         │
         │ Produces
         ▼
┌────────────────┐      ┌──────────────────┐
│  FactorScore   │      │   ErrorPolicy    │
│                │      │                  │
│ - ticker       │      │ - policy_type    │
│ - factor       │      │ - ticker         │
│ - score        │      │ - factor         │
│ - timestamp    │      │ - error_msg      │
│ - metadata     │      └──────────────────┘
└────────────────┘
```

## Core Entities

### 1. Ticker

**Purpose**: Represents a stock symbol with associated metadata

**Attributes**:
| Attribute | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| symbol | str | Yes | - | Uppercase, 1-5 chars, alphanumeric | Stock ticker symbol (e.g., "AAPL") |
| name | str | None | None | - | Company name (e.g., "Apple Inc.") |
| exchange | str | None | None | - | Exchange code (e.g., "NASDAQ") |
| sector | str | None | None | - | Industry sector (e.g., "Technology") |
| is_active | bool | No | True | - | Whether ticker is currently trading |

**Relationships**:
- Has many `StockData` records (one per date)
- Has many `Returns` records (one per date)
- Belongs to one `StockPack`
- Has many `FactorScore` records (one per factor)

**Validation Rules**:
1. `symbol` must be uppercase (auto-convert on creation)
2. `symbol` must be 1-5 characters (most tickers fit this)
3. `symbol` must be alphanumeric (no special chars except "^" for indices)
4. If `is_active=False`, log warning when fetching data

**State Transitions**: None (immutable after creation)

**Example**:
```python
@dataclass(frozen=True)
class Ticker:
    symbol: str
    name: str | None = None
    exchange: str | None = None
    sector: str | None = None
    is_active: bool = True

    def __post_init__(self):
        # Validate and normalize symbol
        object.__setattr__(self, "symbol", self.symbol.upper())
        if not 1 <= len(self.symbol) <= 5:
            raise ValidationError(f"Invalid ticker length: {self.symbol}")
        if not self.symbol.replace("^", "").isalnum():
            raise ValidationError(f"Invalid ticker format: {self.symbol}")
```

### 2. DateRange

**Purpose**: Represents a time period for data queries with validation

**Attributes**:
| Attribute | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| start_date | date | Yes | - | <= end_date, not in future | Start of range (inclusive) |
| end_date | date | Yes | - | >= start_date, not in future | End of range (inclusive) |

**Relationships**:
- Belongs to one `StockPack`

**Validation Rules**:
1. `start_date` must be <= `end_date`
2. `end_date` must not be in the future (cannot fetch future data)
3. `start_date` should not be before 1970-01-01 (API limitations)
4. Range should be <= 50 years (warn if exceeded, may hit API limits)

**State Transitions**: None (immutable)

**Example**:
```python
from datetime import date
from dataclasses import dataclass

@dataclass(frozen=True)
class DateRange:
    start_date: date
    end_date: date

    def __post_init__(self):
        if self.start_date > self.end_date:
            raise ValidationError("start_date must be <= end_date")
        if self.end_date > date.today():
            raise ValidationError("end_date cannot be in future")
        if self.start_date < date(1970, 1, 1):
            logger.warning(f"start_date {self.start_date} is very old, data may be unavailable")
        if (self.end_date - self.start_date).days > 365 * 50:
            logger.warning(f"Date range >50 years, may encounter API limits")

    def __len__(self) -> int:
        """Return number of days in range."""
        return (self.end_date - self.start_date).days + 1

    def business_days(self) -> int:
        """Return number of business days (approx)."""
        return len(pd.bdate_range(self.start_date, self.end_date))
```

### 3. StockData

**Purpose**: Represents one day of historical price/volume data for a ticker

**Attributes**:
| Attribute | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| ticker | Ticker | Yes | - | - | Stock ticker reference |
| date | date | Yes | - | Not in future | Trading date |
| open | Decimal | Yes | - | > 0 | Opening price |
| high | Decimal | Yes | - | > 0, >= open/close | Highest price |
| low | Decimal | Yes | - | > 0, <= open/close | Lowest price |
| close | Decimal | Yes | - | > 0 | Closing price |
| volume | int | Yes | - | >= 0 | Trading volume (shares) |
| adjusted_close | Decimal | Yes | - | > 0 | Split/dividend adjusted close |

**Relationships**:
- Belongs to one `Ticker`
- Used to calculate one `Returns` record

**Validation Rules**:
1. All prices must be > 0 (negative prices impossible)
2. `high` must be >= `open`, `close`, `low`
3. `low` must be <= `open`, `close`, `high`
4. `volume` must be >= 0 (can be 0 for after-hours or thin markets)
5. `adjusted_close` should be close to `close` (if >50% diff, warn of split/dividend)
6. `date` must be a valid trading day (not future, ideally business day)

**State Transitions**: None (immutable, historical data)

**Example**:
```python
from decimal import Decimal
from dataclasses import dataclass

@dataclass(frozen=True)
class StockData:
    ticker: Ticker
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    adjusted_close: Decimal

    def __post_init__(self):
        # Validate price positivity
        for price_field in ["open", "high", "low", "close", "adjusted_close"]:
            price = getattr(self, price_field)
            if price <= 0:
                raise ValidationError(f"{price_field} must be > 0, got {price}")

        # Validate high/low relationships
        if self.high < max(self.open, self.close):
            raise ValidationError(f"high ({self.high}) < max(open, close)")
        if self.low > min(self.open, self.close):
            raise ValidationError(f"low ({self.low}) > min(open, close)")

        # Validate volume
        if self.volume < 0:
            raise ValidationError(f"volume must be >= 0, got {self.volume}")

        # Warn if adjusted_close very different from close (split/dividend)
        if abs(self.adjusted_close - self.close) / self.close > 0.5:
            logger.info(f"[{self.ticker.symbol}] {self.date}: Large adj_close diff (split/dividend?)")

    def daily_return(self, previous_close: Decimal) -> Decimal:
        """Calculate simple return vs previous close."""
        return (self.close - previous_close) / previous_close
```

### 4. Returns

**Purpose**: Represents calculated returns for a ticker on a specific date

**Attributes**:
| Attribute | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| ticker | Ticker | Yes | - | - | Stock ticker reference |
| date | date | Yes | - | - | Date of return calculation |
| simple_return | Decimal | Yes | - | Not inf | Simple return: (P_t - P_t-1) / P_t-1 |
| log_return | Decimal | Yes | - | Not inf | Log return: ln(P_t / P_t-1) |
| period | str | Yes | - | Valid period code | Period type (e.g., "1D", "1W", "1M") |

**Relationships**:
- Belongs to one `Ticker`
- Derived from `StockData` for date and date-1

**Validation Rules**:
1. `simple_return` and `log_return` must not be inf or NaN
2. `simple_return` should be >= -1.0 (can't lose more than 100%)
3. Extreme returns (>100% daily) should log warning (data quality check)
4. `period` must be valid code: "1D" (daily), "1W" (weekly), "1M" (monthly)

**State Transitions**: None (immutable, derived data)

**Example**:
```python
from decimal import Decimal
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class Returns:
    ticker: Ticker
    date: date
    simple_return: Decimal
    log_return: Decimal
    period: str = "1D"

    def __post_init__(self):
        # Validate returns are finite
        if math.isinf(self.simple_return) or math.isnan(self.simple_return):
            raise ValidationError(f"simple_return is inf/NaN for {self.ticker.symbol} on {self.date}")
        if math.isinf(self.log_return) or math.isnan(self.log_return):
            raise ValidationError(f"log_return is inf/NaN for {self.ticker.symbol} on {self.date}")

        # Validate simple return >= -1.0
        if self.simple_return < -1.0:
            raise ValidationError(f"simple_return {self.simple_return} < -1.0 (impossible)")

        # Warn on extreme returns
        if abs(self.simple_return) > 1.0:
            logger.warning(f"[{self.ticker.symbol}] {self.date}: Extreme return {self.simple_return:.2%}")

        # Validate period code
        valid_periods = {"1D", "1W", "1M", "1Q", "1Y"}
        if self.period not in valid_periods:
            raise ValidationError(f"Invalid period '{self.period}', must be one of {valid_periods}")

    def annualized(self, trading_days: int = 252) -> Decimal:
        """Annualize return based on period."""
        if self.period == "1D":
            return self.simple_return * trading_days
        elif self.period == "1W":
            return self.simple_return * 52
        elif self.period == "1M":
            return self.simple_return * 12
        elif self.period == "1Y":
            return self.simple_return
        else:
            raise ValueError(f"Cannot annualize period '{self.period}'")
```

### 5. StockPack

**Purpose**: Represents the complete output package with metadata

**Attributes**:
| Attribute | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| tickers | List[Ticker] | Yes | - | Non-empty | List of tickers included |
| date_range | DateRange | Yes | - | - | Date range for data |
| generation_timestamp | datetime | Yes | - | - | When pack was generated |
| excel_file_path | str | Yes | - | Valid path | Path to output Excel file |
| metadata | dict | No | {} | - | Additional metadata (logs, config used) |

**Relationships**:
- Contains many `Ticker` objects
- Has one `DateRange`

**Validation Rules**:
1. `tickers` list must not be empty
2. `excel_file_path` must be valid file path
3. `generation_timestamp` must not be in future
4. `metadata` should include: config_used, successful_tickers, failed_tickers, cache_hits

**State Transitions**: None (immutable, represents completed operation)

**Example**:
```python
from datetime import datetime
from dataclasses import dataclass, field

@dataclass(frozen=True)
class StockPack:
    tickers: list[Ticker]
    date_range: DateRange
    generation_timestamp: datetime
    excel_file_path: str
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.tickers:
            raise ValidationError("tickers list must not be empty")
        if self.generation_timestamp > datetime.now():
            raise ValidationError("generation_timestamp cannot be in future")
        if not self.excel_file_path.endswith(".xlsx"):
            logger.warning(f"excel_file_path '{self.excel_file_path}' does not end with .xlsx")

    def success_rate(self) -> float:
        """Calculate percentage of successful ticker fetches."""
        total = self.metadata.get("total_tickers", len(self.tickers))
        failed = len(self.metadata.get("failed_tickers", []))
        return (total - failed) / total if total > 0 else 0.0

    def summary(self) -> str:
        """Return human-readable summary."""
        return (
            f"StockPack: {len(self.tickers)} tickers, "
            f"{self.date_range.start_date} to {self.date_range.end_date}, "
            f"generated {self.generation_timestamp}, "
            f"output: {self.excel_file_path}"
        )
```

## Factor Modeling Entities

### 6. Factor (Abstract Interface)

**Purpose**: Abstract base class defining contract for all factor implementations

**Attributes**:
| Attribute | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| name | str (property) | Yes | - | Non-empty, unique | Factor name identifier |
| description | str (property) | No | "" | - | Human-readable description |

**Methods**:
| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| calculate | ticker_data: DataFrame | float | Calculate factor score |
| get_requirements | - | List[str] | Declare data dependencies |

**Validation Rules**:
1. `name` must be unique across all registered factors
2. `name` should be lowercase with underscores (e.g., "momentum", "volatility_30d")
3. `calculate()` must return finite float (not inf/NaN)
4. `get_requirements()` must return list of strings matching available data fields

**Example**:
```python
from abc import ABC, abstractmethod
import pandas as pd

class FactorInterface(ABC):
    """Abstract base class for all factors."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return factor name (unique identifier)."""
        pass

    @property
    def description(self) -> str:
        """Return factor description (optional)."""
        return ""

    @abstractmethod
    def calculate(self, ticker_data: pd.DataFrame) -> float:
        """
        Calculate factor score for a ticker.

        Args:
            ticker_data: DataFrame with columns: date, open, high, low, close, volume, adj_close

        Returns:
            Factor score (float)

        Raises:
            FactorCalculationError: If calculation fails
        """
        pass

    @abstractmethod
    def get_requirements(self) -> list[str]:
        """
        Declare data requirements.

        Returns:
            List of required data fields (e.g., ["price_history", "volume"])

        Available fields:
            - "price_history": OHLC data
            - "volume": Volume data
            - "adjusted_close": Split/dividend adjusted prices
            - "returns": Pre-calculated returns
        """
        pass
```

### 7. FactorScore

**Purpose**: Represents the output of applying a factor to a ticker

**Attributes**:
| Attribute | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| ticker | Ticker | Yes | - | - | Stock ticker reference |
| factor | FactorInterface | Yes | - | - | Factor used for calculation |
| score | Decimal | Yes | - | Finite | Calculated score |
| calculation_date | datetime | Yes | - | - | When score was calculated |
| metadata | dict | No | {} | - | Additional context (data range, params) |

**Relationships**:
- Belongs to one `Ticker`
- References one `Factor`

**Validation Rules**:
1. `score` must be finite (not inf/NaN)
2. `calculation_date` must not be in future
3. `metadata` should include: date_range_used, data_points_count, factor_params

**State Transitions**: None (immutable, point-in-time calculation)

**Example**:
```python
from decimal import Decimal
from datetime import datetime
from dataclasses import dataclass, field

@dataclass(frozen=True)
class FactorScore:
    ticker: Ticker
    factor: FactorInterface
    score: Decimal
    calculation_date: datetime
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if math.isinf(self.score) or math.isnan(self.score):
            raise ValidationError(f"score is inf/NaN for {self.ticker.symbol} + {self.factor.name}")
        if self.calculation_date > datetime.now():
            raise ValidationError("calculation_date cannot be in future")

    def to_dict(self) -> dict:
        """Serialize to dictionary for export."""
        return {
            "ticker": self.ticker.symbol,
            "factor": self.factor.name,
            "score": float(self.score),
            "calculation_date": self.calculation_date.isoformat(),
            "metadata": self.metadata
        }
```

### 8. ErrorPolicy

**Purpose**: Represents how the system handles missing data or calculation failures

**Attributes**:
| Attribute | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| policy_type | Enum | Yes | - | SKIP/LOG/FAIL | Error handling strategy |
| ticker | Ticker | None | None | - | Ticker where error occurred |
| factor | FactorInterface | None | None | - | Factor that failed |
| error_message | str | Yes | - | Non-empty | Description of error |

**Validation Rules**:
1. `policy_type` must be one of: SKIP, LOG, FAIL
2. If `ticker` or `factor` provided, error_message should reference them
3. `error_message` must be actionable (suggest remediation)

**State Transitions**:
- Created when error occurs
- Logged or raised based on policy_type
- Immutable once created

**Example**:
```python
from enum import Enum
from dataclasses import dataclass

class ErrorPolicyType(Enum):
    SKIP = "skip"    # Skip ticker-factor combination, log warning
    LOG = "log"      # Record error in metadata, continue processing
    FAIL = "fail"    # Halt processing, raise exception

@dataclass(frozen=True)
class ErrorPolicy:
    policy_type: ErrorPolicyType
    error_message: str
    ticker: Ticker | None = None
    factor: FactorInterface | None = None

    def __post_init__(self):
        if not self.error_message:
            raise ValidationError("error_message must not be empty")

    def apply(self):
        """Execute policy (skip/log/fail)."""
        context = ""
        if self.ticker:
            context += f"[{self.ticker.symbol}]"
        if self.factor:
            context += f"[{self.factor.name}]"

        full_message = f"{context} {self.error_message}"

        if self.policy_type == ErrorPolicyType.SKIP:
            logger.warning(f"SKIP: {full_message}")
        elif self.policy_type == ErrorPolicyType.LOG:
            logger.error(f"LOG: {full_message}")
        elif self.policy_type == ErrorPolicyType.FAIL:
            raise FactorCalculationError(full_message)
```

## Configuration Entities

### 9. StockPackConfig (Pydantic Model)

**Purpose**: Validated configuration for stock pack generation

**Schema**:
```python
from pydantic import BaseModel, Field, field_validator

class DataSourceConfig(BaseModel):
    provider: str = Field(..., pattern="^(yfinance|alpha_vantage)$")
    api_key: str | None = None
    timeout: int = Field(default=30, gt=0, le=300)

    @field_validator("api_key")
    def validate_api_key(cls, v, info):
        if info.data.get("provider") == "alpha_vantage" and not v:
            raise ValueError("API key required for alpha_vantage")
        return v

class CacheConfig(BaseModel):
    enabled: bool = True
    directory: str = ".cache/stock_data"
    ttl_seconds: int = Field(default=3600, gt=0, le=86400)  # 1 hour to 1 day

class RateLimitConfig(BaseModel):
    requests_per_second: float = Field(default=5.0, gt=0, le=100)
    max_retries: int = Field(default=3, ge=0, le=10)

class LoggingConfig(BaseModel):
    level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: str = "logs/stock_pack.log"

class StockPackConfig(BaseModel):
    data_source: DataSourceConfig
    cache: CacheConfig
    rate_limit: RateLimitConfig
    logging: LoggingConfig
```

## Entity Lifecycle

### Stock Pack Generation Lifecycle

1. **Input Validation**:
   - User provides: tickers (list), date_range (start/end)
   - Create `Ticker` objects (validate format)
   - Create `DateRange` object (validate start <= end, not future)

2. **Data Fetching**:
   - For each `Ticker`:
     - Check cache (DataCache.get_cached)
     - If miss: RateLimiter.wait_if_needed()
     - Fetch from API → create `StockData` records
     - Validate `StockData` (positive prices, high/low relationships)
     - Cache response (DataCache.set_cached)

3. **Processing**:
   - Calculate returns → create `Returns` records
   - Validate returns (finite, >= -1.0)
   - Handle gaps (forward fill, log warnings)

4. **Building**:
   - Create Excel workbook (ExcelBuilder)
   - Add field dictionary sheet
   - Add returns data sheet
   - Add metadata/logs sheet
   - Embed hyperlinks

5. **Output**:
   - Save Excel file
   - Create `StockPack` object (with metadata)
   - Log success
   - Return `StockPack` to user

### Factor Modeling Lifecycle

1. **Factor Registration**:
   - User implements `FactorInterface`
   - Call `FactorRegistry.register(factor)`
   - Validate interface completeness
   - Check for name collisions
   - Store in registry

2. **Configuration Loading**:
   - Load factor requirements YAML
   - Validate schema (pydantic)
   - Detect circular dependencies
   - Log configuration

3. **Factor Calculation**:
   - For each ticker-factor pair:
     - Check requirements (FactorRunner.check_requirements)
     - If missing: create `ErrorPolicy`, apply policy
     - If met: call factor.calculate(data)
     - Create `FactorScore` (validate finite)
     - Log result

4. **Output**:
   - Collect all `FactorScore` objects
   - Export to CSV/JSON/Excel
   - Include metadata (timestamp, config used)

## Validation Summary

| Entity | Key Validations | Error Handling |
|--------|----------------|----------------|
| Ticker | Symbol format (1-5 chars, uppercase, alphanumeric) | Raise ValidationError |
| DateRange | start <= end, not future, not too old/long | Raise ValidationError, log warnings |
| StockData | Prices > 0, high >= open/close, low <= open/close | Raise ValidationError |
| Returns | Finite, >= -1.0, extreme returns warned | Raise ValidationError, log warnings |
| StockPack | Non-empty tickers, valid file path | Raise ValidationError |
| Factor | Unique name, calculate returns finite, requirements valid | Raise FactorValidationError |
| FactorScore | Finite score, timestamp not future | Raise ValidationError |
| ErrorPolicy | Valid policy type, non-empty message | Raise ValidationError |
| Config | Schema validation (pydantic), API key for providers | Raise ConfigError |

All entities use dataclasses (immutable, type-safe) or pydantic models (validated). Validation rules align with Hormax Constitution II (Type Safety) and III (Error Handling).
