# Quickstart Guide: Finance Stocks Module

**Feature**: Finance Stocks Module - Stock Pack Builder & Modeling Framework
**Branch**: `001-en-as-the`
**Date**: 2025-10-14
**Audience**: End users (financial analysts, quantitative researchers)

## Overview

The Finance Stocks Module enables you to generate comprehensive stock analysis reports (Excel files) and apply custom factor models for stock scoring. This guide covers the MVP (Stock Pack Builder) and the full feature (Factor Modeling).

## Prerequisites

- Python 3.11+
- Hormax package installed: `pip install hormax`
- Internet connection (for fetching stock data)
- Excel 2016+ or LibreOffice Calc (for viewing output)

## Quick Start: Generate Your First Stock Pack

### Step 1: Install Hormax

```bash
pip install hormax
```

### Step 2: Create a Configuration File (Optional)

Create `config/stock_pack.yaml` in your working directory:

```yaml
data_source:
  provider: "yfinance"  # Free, no API key required
  timeout: 30

cache:
  enabled: true
  directory: ".cache/stock_data"
  ttl_seconds: 3600  # Cache data for 1 hour

rate_limit:
  requests_per_second: 5.0
  max_retries: 3

logging:
  level: "INFO"
  file: "logs/stock_pack.log"
```

**Note**: If you don't provide a config file, default settings will be used.

### Step 3: Generate a Stock Pack (Python API)

```python
from hormax.finance.stocks import build_stock_pack
from datetime import date

# Generate stock pack for 3 tickers over 2024
pack = build_stock_pack(
    tickers=["AAPL", "MSFT", "GOOGL"],
    start_date="2024-01-01",
    end_date="2024-12-31",
    output_path="my_first_stock_pack.xlsx"
)

print(f"Stock pack generated: {pack.excel_file_path}")
print(f"Success rate: {pack.success_rate():.1%}")
print(f"Generation time: {pack.generation_timestamp}")
```

**Expected Output**:
```
INFO - Fetching data for AAPL...
INFO - Fetching data for MSFT...
INFO - Fetching data for GOOGL...
INFO - Calculating returns...
INFO - Building Excel file...
INFO - Stock pack generated successfully!

Stock pack generated: my_first_stock_pack.xlsx
Success rate: 100.0%
Generation time: 2025-10-14 10:15:32
```

### Step 4: Open the Excel File

Open `my_first_stock_pack.xlsx` in Excel or LibreOffice Calc. You'll see:

**Sheet 1: Field Dictionary**
- Field name, type, description, source URL for every data column
- Hyperlinks to documentation (clickable)

**Sheet 2: Returns**
- Ticker, date, open, high, low, close, volume, adjusted_close
- Simple returns (daily %), log returns
- All data formatted for analysis

**Sheet 3: Metadata & Logs**
- Generation timestamp
- Input parameters (tickers, date range, config used)
- Success/failure logs for each ticker
- Cache hit/miss stats

## Advanced Usage: Command-Line Interface (CLI)

### Generate Stock Pack via CLI

```bash
hormax stocks build \
  --tickers AAPL MSFT GOOGL \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --output my_pack.xlsx \
  --config config/stock_pack.yaml
```

**Output**:
```
Fetching data for AAPL... ✓
Fetching data for MSFT... ✓
Fetching data for GOOGL... ✓
Calculating returns... ✓
Building Excel file... ✓

Stock pack generated successfully!
Tickers: AAPL, MSFT, GOOGL (3 total, 3 successful)
Date range: 2024-01-01 to 2024-12-31
Output: my_pack.xlsx
Generation time: 42.3 seconds
```

### Validate Tickers Before Processing

```python
from hormax.finance.stocks import validate_tickers

results = validate_tickers(["AAPL", "INVALID123", "MSFT"])
print(results)
# Output: {"AAPL": True, "INVALID123": False, "MSFT": True}

# Use valid tickers only
valid_tickers = [ticker for ticker, is_valid in results.items() if is_valid]
pack = build_stock_pack(valid_tickers, "2024-01-01", "2024-12-31", "output.xlsx")
```

## Factor Modeling (Full Feature)

### Step 1: Define a Custom Factor

```python
from hormax.finance.stocks.modeling import FactorInterface
import pandas as pd

class MomentumFactor(FactorInterface):
    """30-day price momentum factor."""

    @property
    def name(self) -> str:
        return "momentum_30d"

    @property
    def description(self) -> str:
        return "30-day rolling return (momentum indicator)"

    def calculate(self, ticker_data: pd.DataFrame) -> float:
        """
        Calculate 30-day momentum.

        Args:
            ticker_data: DataFrame with columns: date, close, ...

        Returns:
            30-day return (percent)
        """
        if len(ticker_data) < 30:
            raise ValueError("Insufficient data: need at least 30 days")

        returns = ticker_data["close"].pct_change(30)
        return float(returns.iloc[-1])  # Most recent 30-day return

    def get_requirements(self) -> list[str]:
        """Declare data requirements."""
        return ["price_history", "adjusted_close"]
```

### Step 2: Register the Factor

```python
from hormax.finance.stocks.modeling import register_factor

# Register your custom factor
momentum = MomentumFactor()
register_factor(momentum)

print(f"Registered factor: {momentum.name}")
```

### Step 3: Calculate Factor Scores

```python
from hormax.finance.stocks.modeling import calculate_factors

# Calculate momentum for multiple tickers
scores_df = calculate_factors(
    tickers=["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"],
    factors=["momentum_30d"],
    date_range=("2024-01-01", "2024-12-31"),
    error_policy="skip"  # Skip tickers with missing data
)

print(scores_df)
```

**Output**:
```
  ticker        factor     score           timestamp
0   AAPL  momentum_30d      0.05 2025-10-14 10:20:00
1   MSFT  momentum_30d      0.03 2025-10-14 10:20:00
2  GOOGL  momentum_30d     -0.01 2025-10-14 10:20:00
3   TSLA  momentum_30d      0.12 2025-10-14 10:20:00
4   NVDA  momentum_30d      0.08 2025-10-14 10:20:00
```

### Step 4: Export Scores

```python
# Export to CSV
scores_df.to_csv("factor_scores.csv", index=False)

# Export to Excel
scores_df.to_excel("factor_scores.xlsx", index=False)

# Export to JSON
scores_df.to_json("factor_scores.json", orient="records", indent=2)
```

### Step 5: Register Multiple Factors

```python
class VolatilityFactor(FactorInterface):
    """60-day price volatility factor."""

    @property
    def name(self) -> str:
        return "volatility_60d"

    def calculate(self, ticker_data: pd.DataFrame) -> float:
        if len(ticker_data) < 60:
            raise ValueError("Insufficient data: need at least 60 days")

        returns = ticker_data["close"].pct_change()
        volatility = returns.tail(60).std()
        return float(volatility)

    def get_requirements(self) -> list[str]:
        return ["price_history"]

# Register multiple factors
register_factor(VolatilityFactor())

# Calculate both factors
scores_df = calculate_factors(
    tickers=["AAPL", "MSFT"],
    factors=["momentum_30d", "volatility_60d"],
    date_range=("2024-01-01", "2024-12-31")
)

print(scores_df)
```

**Output**:
```
  ticker          factor     score           timestamp
0   AAPL    momentum_30d      0.05 2025-10-14 10:25:00
1   AAPL  volatility_60d      0.23 2025-10-14 10:25:00
2   MSFT    momentum_30d      0.03 2025-10-14 10:25:00
3   MSFT  volatility_60d      0.18 2025-10-14 10:25:00
```

## Configuration: Factor Requirements

Create `config/factor_requirements.yaml` to define data dependencies:

```yaml
factors:
  - name: "momentum_30d"
    requirements:
      - "price_history"
      - "adjusted_close"
    min_data_points: 30

  - name: "volatility_60d"
    requirements:
      - "price_history"
      - "returns"
    min_data_points: 60
```

The system will automatically validate requirements before calculation and handle missing data according to your error policy.

## Error Policies

**SKIP** (default): Skip ticker-factor combinations with missing data, log warning
```python
scores = calculate_factors(..., error_policy="skip")
# Missing data → warning logged, no score for that combo
```

**LOG**: Record error but continue, output score=NaN
```python
scores = calculate_factors(..., error_policy="log")
# Missing data → error logged, row included with NaN score
```

**FAIL**: Halt processing on first error
```python
try:
    scores = calculate_factors(..., error_policy="fail")
except FactorCalculationError as e:
    print(f"Factor calculation failed: {e}")
    # Missing data → exception raised, processing stops
```

## Environment Variable Overrides

Override config values via environment variables:

```bash
# Override data source provider
export HORMAX_DATA_SOURCE_PROVIDER="alpha_vantage"
export HORMAX_DATA_SOURCE_API_KEY="your_api_key_here"

# Override cache TTL (1 day instead of 1 hour)
export HORMAX_CACHE_TTL_SECONDS=86400

# Override logging level
export HORMAX_LOGGING_LEVEL="DEBUG"

# Run your script
python my_analysis.py
```

## Common Use Cases

### Use Case 1: Weekly Stock Pack for Portfolio

```python
from hormax.finance.stocks import build_stock_pack
from datetime import date, timedelta

# My portfolio tickers
portfolio = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

# Last 30 days
end_date = date.today()
start_date = end_date - timedelta(days=30)

# Generate weekly pack
pack = build_stock_pack(
    tickers=portfolio,
    start_date=start_date,
    end_date=end_date,
    output_path=f"portfolio_{end_date.isoformat()}.xlsx"
)

print(f"Portfolio pack saved: {pack.excel_file_path}")
```

### Use Case 2: Momentum Screening for 50 Stocks

```python
from hormax.finance.stocks.modeling import calculate_factors

# S&P 500 top 50 by market cap (example)
sp500_top50 = ["AAPL", "MSFT", "GOOGL", ...]  # 50 tickers

# Calculate momentum for all
scores = calculate_factors(
    tickers=sp500_top50,
    factors=["momentum_30d"],
    date_range=("2024-01-01", "2024-12-31"),
    error_policy="skip"
)

# Sort by momentum score (descending)
top_movers = scores.sort_values("score", ascending=False).head(10)
print("Top 10 momentum stocks:")
print(top_movers)
```

### Use Case 3: Multi-Factor Screening

```python
# Register multiple factors
register_factor(MomentumFactor())
register_factor(VolatilityFactor())
# ... register more factors ...

# Calculate all factors for watchlist
watchlist = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
scores = calculate_factors(
    tickers=watchlist,
    factors=["momentum_30d", "volatility_60d", "..."],
    date_range=("2024-01-01", "2024-12-31")
)

# Pivot for analysis
pivot = scores.pivot(index="ticker", columns="factor", values="score")
print(pivot)
```

**Output**:
```
factor  momentum_30d  volatility_60d  ...
ticker
AAPL            0.05            0.23  ...
GOOGL          -0.01            0.19  ...
MSFT            0.03            0.18  ...
NVDA            0.08            0.35  ...
TSLA            0.12            0.42  ...
```

## Troubleshooting

### Issue: "Ticker not found" Error

**Problem**: `StockDataError: [XYZ] Failed to fetch stock data: 404 Not Found`

**Solution**:
1. Verify ticker symbol is correct (check exchange website)
2. Try with `validate_tickers()` first
3. Check if ticker is delisted (set `is_active=False`)

### Issue: Slow Performance

**Problem**: Generating pack for 100 tickers takes >10 minutes

**Solution**:
1. Enable caching in config (`cache.enabled: true`)
2. Reduce rate limit if hitting API throttling
3. Split into multiple smaller packs
4. Use `alpha_vantage` if yfinance is slow

### Issue: Excel File Empty or Corrupted

**Problem**: Excel file opens but shows no data

**Solution**:
1. Check logs for errors during Excel generation
2. Verify output path is writable
3. Ensure openpyxl is installed: `pip install openpyxl`
4. Check file size (if >10MB, may need Excel 64-bit)

### Issue: Factor Calculation Fails

**Problem**: `FactorCalculationError: Insufficient data`

**Solution**:
1. Check `min_data_points` in factor requirements config
2. Extend date range to include more historical data
3. Use `error_policy="skip"` to skip problematic tickers
4. Verify factor requirements match available data

## Next Steps

1. **Read the API Documentation**: `contracts/stock_pack_api.md`
2. **Review Data Model**: `data-model.md` (entity definitions)
3. **Customize Configuration**: Edit `config/stock_pack.yaml`
4. **Build Custom Factors**: Implement `FactorInterface` for your models
5. **Integrate with Notebooks**: Use in Jupyter notebooks for interactive analysis

## Support

- **Documentation**: `/specs/001-en-as-the/`
- **Issues**: Report bugs via project issue tracker
- **Examples**: See `examples/` directory for more use cases

---

**Happy analyzing!**
