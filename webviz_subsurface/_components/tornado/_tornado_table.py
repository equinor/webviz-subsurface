from webviz_subsurface._utils.formatting import printable_int_list
from ._tornado_data import TornadoData


class TornadoTable:
    """Creates `data`for a `dash_table.DataTable` from a TornadaData instance."""

    COLUMNS = [
        "Sensitivity",
        "Low Case",
        "High Case",
        "Delta low",
        "Delta high",
        "True low",
        "True high",
        "Low reals",
        "High reals",
    ]

    def __init__(
        self,
        tornado_data: TornadoData,
    ) -> None:
        self._table = tornado_data.tornadotable.copy()
        self._table["Delta low"] = (
            self._table["true_low"].astype("float") - tornado_data.reference_average
        )
        self._table["Delta high"] = (
            self._table["true_high"].astype("float") - tornado_data.reference_average
        )
        self._table["low_reals"] = self._table["low_reals"].apply(printable_int_list)
        self._table["high_reals"] = self._table["high_reals"].apply(printable_int_list)

        self._table.rename(
            columns={
                "sensname": "Sensitivity",
                "low": "Low Case",
                "high": "High Case",
                "true_low": "True low",
                "true_high": "True high",
                "low_reals": "Low reals",
                "high_reals": "High reals",
            },
            inplace=True,
        )

    @property
    def as_plotly_table(self) -> dict:
        return self._table.iloc[::-1].to_dict("records")
