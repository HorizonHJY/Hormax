"""Demo script for stock pack builder.

This script demonstrates how to use the stock pack builder
to generate a stock data pack with sample tickers.
"""

from datetime import date
from pathlib import Path
import sys


# Ensure the repository root is on ``sys.path`` when the script is executed
# directly (``python hormax/demo_stock_pack.py``).  Without this, Python
# resolves the ``hormax`` package to ``hormax/hormax`` which only contains
# namespace stubs, leading to ``ModuleNotFoundError`` for the real
# implementation that lives one directory higher.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hormax.finance.stocks import build_stock_pack


def main() -> None:
    """Run the demo stock pack generation."""
    # Configuration
    tickers = ["AAPL", "MSFT", "GOOGL"]
    start_date = date(2023, 1, 1)
    end_date = date(2023, 12, 31)
    output_path = Path("output/stock_pack_demo.xlsx")

    print("=" * 60)
    print("Stock Pack Builder Demo")
    print("=" * 60)
    print(f"Tickers: {', '.join(tickers)}")
    print(f"Date Range: {start_date} to {end_date}")
    print(f"Output: {output_path}")
    print("=" * 60)
    print()

    try:
        # Build the stock pack
        print("Building stock pack...")
        stock_pack = build_stock_pack(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            output_path=output_path,
        )

        print()
        print("=" * 60)
        print("Stock Pack Built Successfully!")
        print("=" * 60)
        print(f"Number of tickers: {stock_pack.get_ticker_count()}")
        print(f"Date range days: {stock_pack.get_date_range_days()}")
        print(f"Output file: {output_path.absolute()}")
        print()

        # Display summary statistics
        print("Summary Statistics:")
        print("-" * 60)
        for ticker in stock_pack.tickers:
            returns = stock_pack.returns[ticker.symbol]
            print(f"{ticker.symbol:6s} | "
                  f"Total Return: {returns.total_return:7.2%} | "
                  f"Ann. Return: {returns.annualized_return:7.2%} | "
                  f"Volatility: {returns.volatility:7.2%}")

        print("=" * 60)

    except Exception as e:
        print(f"ERROR: {e}")
        raise


if __name__ == "__main__":
    main()
