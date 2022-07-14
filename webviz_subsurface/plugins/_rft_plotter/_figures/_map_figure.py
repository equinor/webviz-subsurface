from typing import Any, Dict, List

import pandas as pd


class MapFigure:
    def __init__(self, ertdf: pd.DataFrame, ensemble: str, zones: List[str]) -> None:

        self.ertdf = (
            ertdf.loc[(ertdf["ENSEMBLE"] == ensemble) & (ertdf["ZONE"].isin(zones))]
            .groupby(["WELL", "DATE", "ENSEMBLE"])
            .aggregate("mean")
            .reset_index()
        )
        self.traces: List[Dict[str, Any]] = []

    def add_misfit_plot(self, sizeby: str, colorby: str, dates: List[float]) -> None:
        df = self.ertdf.loc[
            (self.ertdf["DATE_IDX"] >= dates[0]) & (self.ertdf["DATE_IDX"] <= dates[1])
        ]

        self.traces.append(
            {
                "x": df["EAST"],
                "y": df["NORTH"],
                "text": df["WELL"],
                "customdata": df["WELL"],
                "mode": "markers",
                "hovertext": [
                    f"Well: {well}"
                    f"<br>Mean simulated pressure: {pressure:.2f}"
                    f"<br>Mean misfit: {misfit:.2f}"
                    f"<br>Stddev pressure: {stddev:.2f}"
                    for well, stddev, misfit, pressure in zip(
                        df["WELL"], df["STDDEV"], df["DIFF"], df["SIMULATED"]
                    )
                ],
                "hoverinfo": "text",
                # "name": date,
                "showlegend": False,
                "marker": {
                    "size": df[sizeby],
                    "sizeref": 2.0 * self.ertdf[sizeby].quantile(0.9) / (40.0**2),
                    "sizemode": "area",
                    "sizemin": 6,
                    "color": df[colorby],
                    "cmin": self.ertdf[colorby].min(),
                    "cmax": self.ertdf[colorby].quantile(0.9),
                    "colorscale": [[0, "#2584DE"], [1, "#E50000"]],
                    "showscale": True,
                },
            }
        )

    def add_fault_lines(self, df: pd.DataFrame) -> None:
        for _fault, faultdf in df.groupby("POLY_ID"):
            self.traces.append(
                {
                    "x": faultdf["X_UTME"],
                    "y": faultdf["Y_UTMN"],
                    "mode": "lines",
                    "type": "scatter",
                    "hoverinfo": "none",
                    "showlegend": False,
                    "line": {"color": "grey", "width": 1},
                }
            )

    @property
    def layout(self) -> Dict[str, Any]:
        """The plotly figure layout"""
        return {
            "hovermode": "closest",
            "legend": {"itemsizing": "constant", "orientation": "h"},
            "colorway": ["red", "blue"],
            "margin": {"t": 50, "l": 50},
            "xaxis": {"constrain": "domain", "showgrid": False},
            "yaxis": {"scaleanchor": "x", "showgrid": False},
        }
