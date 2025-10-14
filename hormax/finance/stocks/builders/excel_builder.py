"""Excel workbook builder for stock packs.

This module provides functionality for building Excel workbooks
with multiple sheets from stock pack data.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.worksheet.hyperlink import Hyperlink

from hormax.core.logging_setup import get_logger
from hormax.exceptions import StockPackError
from hormax.finance.stocks.builders.field_dictionary import FieldDictionary
from hormax.finance.stocks.entities import StockPack

logger = get_logger(__name__)


class ExcelBuilder:
    """Builder for creating Excel workbooks from stock packs.

    Attributes:
        field_dictionary: Field dictionary for metadata.
    """

    def __init__(self) -> None:
        """Initialize the Excel builder."""
        self.field_dictionary = FieldDictionary()

    def build_workbook(self, stock_pack: StockPack, output_path: Path) -> None:
        """Build an Excel workbook from a stock pack.

        Args:
            stock_pack: Stock pack data to export.
            output_path: Path for the output Excel file.

        Raises:
            StockPackError: If workbook creation fails.
        """
        try:
            logger.info(f"Building Excel workbook with {stock_pack.get_ticker_count()} tickers")

            wb = Workbook()
            # Remove default sheet
            if "Sheet" in wb.sheetnames:
                wb.remove(wb["Sheet"])

            # Add sheets
            self._add_field_dictionary_sheet(wb)
            self._add_summary_sheet(wb, stock_pack)
            self._add_returns_sheets(wb, stock_pack)
            self._add_price_sheets(wb, stock_pack)
            self._add_metadata_sheet(wb, stock_pack)

            # Save workbook
            output_path.parent.mkdir(parents=True, exist_ok=True)
            wb.save(output_path)

            logger.info(f"Excel workbook saved to {output_path}")

        except Exception as e:
            logger.error(f"Failed to build Excel workbook: {e}")
            raise StockPackError(f"Failed to build Excel workbook: {e}") from e

    def _add_field_dictionary_sheet(self, wb: Workbook) -> None:
        """Add field dictionary sheet to workbook.

        Args:
            wb: Workbook to add sheet to.
        """
        ws = wb.create_sheet("Field Dictionary", 0)

        # Convert field dictionary to DataFrame
        fields_data = self.field_dictionary.to_dict()
        df = pd.DataFrame(fields_data)

        # Write data to sheet
        for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), 1):
            for c_idx, value in enumerate(row, 1):
                cell = ws.cell(row=r_idx, column=c_idx, value=value)

                # Style header row
                if r_idx == 1:
                    cell.font = Font(bold=True)
                    cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")

        # Auto-size columns
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            ws.column_dimensions[column_letter].width = min(max_length + 2, 50)

    def _add_summary_sheet(self, wb: Workbook, stock_pack: StockPack) -> None:
        """Add summary sheet with key metrics for all tickers.

        Args:
            wb: Workbook to add sheet to.
            stock_pack: Stock pack data.
        """
        ws = wb.create_sheet("Summary")

        # Prepare summary data
        summary_data = []
        for ticker in stock_pack.tickers:
            returns = stock_pack.returns[ticker.symbol]
            summary_data.append({
                "Ticker": ticker.symbol,
                "Total Return": returns.total_return,
                "Annualized Return": returns.annualized_return,
                "Volatility": returns.volatility,
            })

        df = pd.DataFrame(summary_data)

        # Write data
        for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), 1):
            for c_idx, value in enumerate(row, 1):
                cell = ws.cell(row=r_idx, column=c_idx, value=value)

                # Style header
                if r_idx == 1:
                    cell.font = Font(bold=True)
                    cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
                    cell.font = Font(bold=True, color="FFFFFF")

                # Format percentages
                if r_idx > 1 and c_idx > 1:
                    cell.number_format = "0.00%"

        # Auto-size columns
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            ws.column_dimensions[column_letter].width = max_length + 2

    def _add_returns_sheets(self, wb: Workbook, stock_pack: StockPack) -> None:
        """Add returns data sheets for each ticker.

        Args:
            wb: Workbook to add sheets to.
            stock_pack: Stock pack data.
        """
        for ticker in stock_pack.tickers:
            returns = stock_pack.returns[ticker.symbol]

            # Create DataFrame with returns
            df = pd.DataFrame({
                "Date": returns.daily_returns.index,
                "Daily_Return": returns.daily_returns.values,
                "Cumulative_Return": returns.cumulative_returns.values,
            })

            # Create sheet
            sheet_name = f"{ticker.symbol}_Returns"
            ws = wb.create_sheet(sheet_name)

            # Write data
            for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), 1):
                for c_idx, value in enumerate(row, 1):
                    cell = ws.cell(row=r_idx, column=c_idx, value=value)

                    # Style header
                    if r_idx == 1:
                        cell.font = Font(bold=True)
                        cell.fill = PatternFill(start_color="70AD47", end_color="70AD47", fill_type="solid")
                        cell.font = Font(bold=True, color="FFFFFF")

                    # Format returns as percentages
                    if r_idx > 1 and c_idx > 1:
                        cell.number_format = "0.00%"

    def _add_price_sheets(self, wb: Workbook, stock_pack: StockPack) -> None:
        """Add price data sheets for each ticker.

        Args:
            wb: Workbook to add sheets to.
            stock_pack: Stock pack data.
        """
        for ticker in stock_pack.tickers:
            stock_data = stock_pack.stock_data[ticker.symbol]
            df = stock_data.data.reset_index()

            # Create sheet
            sheet_name = f"{ticker.symbol}_Prices"
            ws = wb.create_sheet(sheet_name)

            # Write data
            for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), 1):
                for c_idx, value in enumerate(row, 1):
                    cell = ws.cell(row=r_idx, column=c_idx, value=value)

                    # Style header
                    if r_idx == 1:
                        cell.font = Font(bold=True)
                        cell.fill = PatternFill(start_color="FFC000", end_color="FFC000", fill_type="solid")
                        cell.font = Font(bold=True, color="FFFFFF")

    def _add_metadata_sheet(self, wb: Workbook, stock_pack: StockPack) -> None:
        """Add metadata sheet with generation info and logs.

        Args:
            wb: Workbook to add sheet to.
            stock_pack: Stock pack data.
        """
        ws = wb.create_sheet("Metadata")

        # Add metadata
        metadata_rows = [
            ("Generated At", stock_pack.created_at.isoformat()),
            ("Date Range", f"{stock_pack.date_range.start} to {stock_pack.date_range.end}"),
            ("Number of Tickers", stock_pack.get_ticker_count()),
            ("Tickers", ", ".join(t.symbol for t in stock_pack.tickers)),
            ("Date Range Days", stock_pack.get_date_range_days()),
        ]

        # Add custom metadata
        for key, value in stock_pack.metadata.items():
            metadata_rows.append((key, str(value)))

        # Write metadata
        for r_idx, (key, value) in enumerate(metadata_rows, 1):
            ws.cell(row=r_idx, column=1, value=key).font = Font(bold=True)
            ws.cell(row=r_idx, column=2, value=value)

        # Auto-size columns
        ws.column_dimensions["A"].width = 20
        ws.column_dimensions["B"].width = 50
