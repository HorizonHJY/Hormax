# Hormax - Stock Pack Builder

Hormax is a Python package for financial data analysis and stock pack generation. It provides a simple API for fetching stock data, calculating returns, and generating comprehensive Excel reports.

## Features

- **Stock Data Fetching**: Retrieve historical stock data using yfinance
- **Data Processing**: Automatic data cleaning and validation
- **Returns Calculation**: Daily returns, cumulative returns, and summary metrics
- **Excel Export**: Multi-sheet Excel workbooks with:
  - Field dictionary
  - Summary statistics
  - Returns data per ticker
  - Price data per ticker
  - Metadata and logs
- **Caching**: Built-in caching to reduce API calls
- **Rate Limiting**: Automatic rate limiting with exponential backoff

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or install in development mode
pip install -e .
```

## Quick Start

```python
from datetime import date
from pathlib import Path
from hormax.finance.stocks import build_stock_pack

# Build a stock pack
stock_pack = build_stock_pack(
    tickers=["AAPL", "MSFT", "GOOGL"],
    start_date=date(2023, 1, 1),
    end_date=date(2023, 12, 31),
    output_path=Path("output/my_stock_pack.xlsx")
)

# Access summary data
for ticker in stock_pack.tickers:
    returns = stock_pack.returns[ticker.symbol]
    print(f"{ticker.symbol}: {returns.total_return:.2%}")
```

## Running the Demo

```bash
python demo_stock_pack.py
```

This will generate a sample stock pack for AAPL, MSFT, and GOOGL with 2023 data.

## Configuration

Create a `config/stock_pack.yaml` file to customize settings:

```yaml
data_source:
  provider: "yfinance"
  timeout: 30

cache:
  enabled: true
  directory: ".cache/stock_data"
  ttl_seconds: 3600

rate_limit:
  requests_per_second: 5.0
  max_retries: 3

logging:
  level: "INFO"
  file: "logs/stock_pack.log"
```

## Project Structure

```
hormax/
├── finance/
│   └── stocks/
│       ├── data_sources/    # Data fetching and caching
│       ├── processors/      # Data cleaning and returns calculation
│       ├── builders/        # Excel workbook generation
│       └── stock_pack_builder.py  # Main orchestration
├── core/
│   ├── config.py           # Configuration management
│   ├── logging_setup.py    # Logging configuration
│   └── validators.py       # Input validation
└── exceptions.py           # Custom exceptions
```

## Development

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black .

# Lint code
ruff check .

# Type checking
mypy hormax
```

## License

MIT License

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.
