import pandas as pd


class CorrelationFigure:
    def __init__(self, series: pd.Series, n_rows: int, title: str):
        self.series = series.tail(n=n_rows)
        self.title = title
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
                "orientation": "h",
                "type": "bar",
                "marker": {},
            }
        ]

    @property
    def layout(self):
        return {
            "barmode": "relative",
            "xaxis": {"range": [-1, 1]},
            "yaxis": {"automargin": True},
            "automargin": True,
        }

    @property
    def first_y_value(self):
        return self.data[0]["y"][-1]

    def set_bar_colors(self, selected_bar):
        self._data[0]["marker"]["color"] = [
            "grey" if _bar != selected_bar else "red" for _bar in self.data[0]["y"]
        ]
