from typing import Any, Dict, List

import numpy as np
import pandas as pd
import webviz_core_components as wcc


def update_misfit_plot(df: pd.DataFrame, enscolors: Dict[str, Any]) -> List[wcc.Graph]:

    max_diff = find_max_diff(df)
    figures = []
    for ens, ensdf in df.groupby("ENSEMBLE"):

        realdf = ensdf.groupby("REAL").sum().reset_index()

        mean_diff = realdf["ABSDIFF"].mean()
        realdf = realdf.sort_values(by=["ABSDIFF"])
        trace = {
            "x": realdf["REAL"],
            "y": realdf["ABSDIFF"],
            "type": "bar",
            "name": ens,
            "marker": {"color": enscolors[ens]},
        }

        layout = {
            "title": {
                "text": ens,
                "y": 0.95,
                "x": 0.15,
                "xanchor": "center",
                "yanchor": "top",
            },
            "height": 400,
            "xaxis": {"type": "category", "title": "Realization"},
            "yaxis": {"range": [0, max_diff], "title": "Cumulative misfit"},
            "shapes": [average_line_shape(mean_diff, "y")],
            "annotations": [average_arrow_annotation(mean_diff, "y")],
            "margin": {"l": 100, "r": 0, "b": 50, "t": 30},
        }

        figures.append(wcc.Graph(figure={"data": [trace], "layout": layout}))
    return figures


def average_line_shape(mean_value: np.float64, yref: str = "y") -> Dict[str, Any]:
    return {
        "type": "line",
        "yref": yref,
        "y0": mean_value,
        "y1": mean_value,
        "xref": "paper",
        "x0": 0,
        "x1": 1,
    }


def average_arrow_annotation(mean_value: np.float64, yref: str = "y") -> Dict[str, Any]:
    return {
        "x": 0.2,
        "y": mean_value,
        "xref": "paper",
        "yref": yref,
        "text": f"Average: {mean_value:.2f}",
        "showarrow": True,
        "align": "center",
        "arrowhead": 2,
        "arrowsize": 1,
        "arrowwidth": 1,
        "arrowcolor": "#636363",
        "ax": 20,
        "ay": -25,
    }


def find_max_diff(df: pd.DataFrame) -> np.float64:
    max_diff = np.float64(0)
    for _ens, ensdf in df.groupby("ENSEMBLE"):
        realdf = ensdf.groupby("REAL").sum().reset_index()
        max_diff = (
            max_diff if max_diff > realdf["ABSDIFF"].max() else realdf["ABSDIFF"].max()
        )
    return max_diff
