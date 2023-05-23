import logging
from typing import Any, Dict, List

import pandas as pd

from ...._types import ColorAndSizeByType


class MapFigure:
    def __init__(self, ertdf: pd.DataFrame, ensemble: str, zones: List[str]) -> None:
        self._ertdf = (
            ertdf.loc[(ertdf["ENSEMBLE"] == ensemble) & (ertdf["ZONE"].isin(zones))]
            .groupby(["WELL", "DATE", "ENSEMBLE"])
            .mean(numeric_only=False)
            .reset_index()
        )

        self._traces: List[Dict[str, Any]] = []

    def add_misfit_plot(
        self,
        sizeby: ColorAndSizeByType,
        colorby: ColorAndSizeByType,
        dates: List[float],
    ) -> None:
        df = self._ertdf.loc[
            (self._ertdf["DATE_IDX"] >= dates[0])
            & (self._ertdf["DATE_IDX"] <= dates[1])
        ]
        self._traces.append(
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
                    "size": df[sizeby.value],
                    "sizeref": 2.0
                    * self._ertdf[sizeby.value].quantile(0.9)
                    / (40.0**2),
                    "sizemode": "area",
                    "sizemin": 6,
                    "color": df[colorby.value],
                    "cmin": self._ertdf[colorby.value].min(),
                    "cmax": self._ertdf[colorby.value].quantile(0.9),
                    "colorscale": [[0, "#2584DE"], [1, "#E50000"]],
                    "showscale": True,
                },
            }
        )

    def add_fault_lines(self, df: pd.DataFrame) -> None:
        cols = df.columns
        if ("ID" in cols) and ("X" in cols) and ("Y" in cols):
            df_polygon = df[["X", "Y", "ID"]]
        elif ("POLY_ID" in cols) and ("X_UTME" in cols) and ("Y_UTMN" in cols):
            df_polygon = df[["X_UTME", "Y_UTMN", "POLY_ID"]].rename(
                columns={"X_UTME": "X", "Y_UTMN": "Y", "POLY_ID": "ID"}
            )
            logging.warning(
                "For the future, consider using X,Y,Z,ID as header names in "
                "the polygon files, as this is regarded as the FMU standard."
                "The current file uses X_UTME,Y_UTMN,POLY_ID."
            )
        else:
            logging.warning(
                "The polygon file does not have an expected "
                "format and is therefore skipped. The file must either "
                "contain the columns 'POLY_ID', 'X_UTME' and 'Y_UTMN' or "
                "the columns 'ID', 'X' and 'Y'."
            )

        for _fault, faultdf in df_polygon.groupby("ID"):
            self._traces.append(
                {
                    "x": faultdf["X"],
                    "y": faultdf["Y"],
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

    @property
    def traces(self) -> List[Dict[str, Any]]:
        """Returns the list of traces"""
        return self._traces
