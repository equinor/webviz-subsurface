import pandas as pd
from .._utils.colors import hex_to_rgba


class BarChart:
    def __init__(self, series: pd.Series, n_rows: int, title: str, orientation: str):
        self.series = series.tail(n=n_rows)
        self.title = title
        self.orientation = orientation
        self._data = self.initial_data

    @property
    def data(self):
        return self._data

    @property
    def figure(self):
        return {"data": self.data, "layout": self.layout}

    @property
    def initial_data(self):
        return [
            {
                "x": self.series.values,
                "y": self.series.index,
                "orientation": self.orientation,
                "type": "bar",
                "marker": {},
            }
        ]

    @property
    def layout(self):
        return {
            "title": self.title,
            "margin": {
                "r": 20,
                "t": 60,
                "b": 20,
            },
            "barmode": "relative",
            "xaxis": {
                "range": [
                    self.series.values.min() - 0.1,
                    self.series.values.max() + 0.1,
                ]
            },
            "yaxis": {"automargin": True},
        }

    @property
    def first_y_value(self):
        return self.data[0]["y"][-1]

    def color_bars(
        self,
        selected_bar: str,
        color: str,
        opacity: float,
        color_selected="#FF1243",
    ) -> None:
        """
        Set colors to the correlation plot bar,
        with separate color for the selected bar
        """
        self._data[0]["marker"] = {
            "color": [
                hex_to_rgba(color, opacity)
                if _bar != selected_bar
                else hex_to_rgba(color_selected, 0.8)
                for _bar in self._data[0]["y"]
            ],
            "line": {
                "color": [
                    color if _bar != selected_bar else color_selected
                    for _bar in self._data[0]["y"]
                ],
                "width": 1.2,
            },
        }
