from typing import Dict, List

from ._tornado_data import TornadoData


class TornadoTable:
    """Creates `data`for a `dash_table.DataTable` from a TornadaData instance."""

    def __init__(
        self,
        tornado_data: TornadoData,
    ) -> None:
        self._table = tornado_data.tornadotable.copy()
        self.scale = tornado_data.scale

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

    @property
    def columns(self) -> List[Dict]:
        return [
            {
                "name": col,
                "id": col,
                "type": "numeric",
                "format": {
                    "locale": {"symbol": ["", ""]},
                    "specifier": "$.4s",
                }
                if not "%" in col
                else {
                    "specifier": ".1f",
                },
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
