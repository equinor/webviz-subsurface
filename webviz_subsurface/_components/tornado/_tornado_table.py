from typing import Dict, List, Union

from dash.dash_table.Format import Format

from ._tornado_data import TornadoData


class TornadoTable:
    """Creates `data`for a `dash_table.DataTable` from a TornadaData instance."""

    def __init__(
        self,
        tornado_data: TornadoData,
        use_si_format: bool = True,
        precision: int = 4,
    ) -> None:
        self._table = tornado_data.tornadotable.copy()
        self.scale = tornado_data.scale
        self._use_si_format = use_si_format
        self._precision = precision
        self._table["low_reals"] = self._table["low_reals"].apply(lambda x: str(len(x)))
        self._table["high_reals"] = self._table["high_reals"].apply(
            lambda x: str(len(x))
        )
        self._table["Response"] = tornado_data.response_name
        self._table.rename(
            columns={
                "sensname": "Sensitivity",
                "low": "Delta low" + (" (%)" if self.scale == "Percentage" else ""),
                "high": "Delta high" + (" (%)" if self.scale == "Percentage" else ""),
                "true_low": "True low",
                "true_high": "True high",
                "low_reals": "Low #reals",
                "high_reals": "High #reals",
            },
            inplace=True,
        )

    def set_column_format(self, col: str) -> Union[dict, Format]:
        if "%" in col:
            return {"specifier": ".1f"}
        if self._use_si_format:
            return {
                "locale": {"symbol": ["", ""]},
                "specifier": f"$.{self._precision}s",
            }
        return Format(precision=self._precision)

    @property
    def columns(self) -> List[Dict]:
        return [
            {
                "name": col,
                "id": col,
                "type": "numeric",
                "format": self.set_column_format(col),
            }
            for col in [
                "Response",
                "Sensitivity",
                "Delta low" + (" (%)" if self.scale == "Percentage" else ""),
                "Delta high" + (" (%)" if self.scale == "Percentage" else ""),
                "True low",
                "True high",
                "Low #reals",
                "High #reals",
            ]
        ]

    @property
    def as_plotly_table(self) -> list:
        return self._table.iloc[::-1].to_dict("records")
