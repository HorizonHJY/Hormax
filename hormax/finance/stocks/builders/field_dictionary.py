"""Field dictionary for stock data pack.

This module provides the field dictionary that describes all data fields
included in the stock pack Excel output.
"""

from typing import Dict, List, NamedTuple


class FieldDefinition(NamedTuple):
    """Definition of a data field.

    Attributes:
        name: Field name.
        description: Human-readable description.
        data_type: Data type (e.g., 'float', 'date', 'string').
        source: Data source or calculation method.
    """

    name: str
    description: str
    data_type: str
    source: str


class FieldDictionary:
    """Field dictionary for stock pack data."""

    def __init__(self) -> None:
        """Initialize the field dictionary with standard fields."""
        self._fields: List[FieldDefinition] = [
            # Price fields
            FieldDefinition(
                name="Date",
                description="Trading date",
                data_type="date",
                source="yfinance",
            ),
            FieldDefinition(
                name="Open",
                description="Opening price for the trading day",
                data_type="float",
                source="yfinance",
            ),
            FieldDefinition(
                name="High",
                description="Highest price during the trading day",
                data_type="float",
                source="yfinance",
            ),
            FieldDefinition(
                name="Low",
                description="Lowest price during the trading day",
                data_type="float",
                source="yfinance",
            ),
            FieldDefinition(
                name="Close",
                description="Closing price for the trading day",
                data_type="float",
                source="yfinance",
            ),
            FieldDefinition(
                name="Volume",
                description="Trading volume (number of shares)",
                data_type="integer",
                source="yfinance",
            ),
            # Returns fields
            FieldDefinition(
                name="Daily_Return",
                description="Daily percentage return (Close-to-Close)",
                data_type="float",
                source="Calculated: (Close_t - Close_t-1) / Close_t-1",
            ),
            FieldDefinition(
                name="Cumulative_Return",
                description="Cumulative return since start date",
                data_type="float",
                source="Calculated: Product of (1 + Daily_Return) - 1",
            ),
            # Summary metrics
            FieldDefinition(
                name="Total_Return",
                description="Total return over the entire period",
                data_type="float",
                source="Calculated: Final cumulative return",
            ),
            FieldDefinition(
                name="Annualized_Return",
                description="Annualized return (CAGR)",
                data_type="float",
                source="Calculated: (1 + Total_Return)^(252/days) - 1",
            ),
            FieldDefinition(
                name="Volatility",
                description="Annualized volatility (standard deviation of returns)",
                data_type="float",
                source="Calculated: Std(Daily_Return) * sqrt(252)",
            ),
            FieldDefinition(
                name="Sharpe_Ratio",
                description="Risk-adjusted return (assuming 2% risk-free rate)",
                data_type="float",
                source="Calculated: (Annualized_Return - 0.02) / Volatility",
            ),
            FieldDefinition(
                name="Max_Drawdown",
                description="Maximum peak-to-trough decline",
                data_type="float",
                source="Calculated: Min((Price - Running_Max) / Running_Max)",
            ),
        ]

    def get_all_fields(self) -> List[FieldDefinition]:
        """Get all field definitions.

        Returns:
            List of all field definitions.
        """
        return self._fields.copy()

    def get_field_by_name(self, name: str) -> FieldDefinition:
        """Get a field definition by name.

        Args:
            name: Field name.

        Returns:
            Field definition.

        Raises:
            KeyError: If field name not found.
        """
        for field in self._fields:
            if field.name == name:
                return field
        raise KeyError(f"Field '{name}' not found in dictionary")

    def add_field(self, field: FieldDefinition) -> None:
        """Add a custom field definition.

        Args:
            field: Field definition to add.
        """
        # Check if field already exists
        for existing in self._fields:
            if existing.name == field.name:
                raise ValueError(f"Field '{field.name}' already exists")

        self._fields.append(field)

    def to_dict(self) -> List[Dict[str, str]]:
        """Convert field dictionary to list of dictionaries.

        Returns:
            List of field definitions as dictionaries.
        """
        return [
            {
                "Field Name": field.name,
                "Description": field.description,
                "Data Type": field.data_type,
                "Source/Calculation": field.source,
            }
            for field in self._fields
        ]
