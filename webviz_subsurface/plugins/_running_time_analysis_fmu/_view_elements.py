from typing import List, Union

import numpy as np
import pandas as pd
from webviz_config.common_cache import CACHE


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def render_matrix(status_df: pd.DataFrame, rel: str, theme: dict) -> dict:
    """Render matrix
    Returns figure object as heatmap for the chosen ensemble and scaling method.
    """
    if rel == "Same job in ensemble":
        z = list(status_df["JOB_SCALED_RUNTIME"])
    elif rel == "Slowest job in realization":
        z = list(status_df["REAL_SCALED_RUNTIME"])
    else:
        z = list(status_df["ENS_SCALED_RUNTIME"])
    data = {
        "type": "heatmap",
        "x": list(status_df["REAL"]),
        "y": list(status_df["JOB_ID"]),
        "z": z,
        "zmin": 0,
        "zmax": 1,
        "text": list(status_df["HOVERINFO"]),
        "hoverinfo": "text",
        "colorscale": theme["layout"]["colorscale"]["sequential"],
        "colorbar": {
            "tickvals": [
                0,
                0.5,
                1,
            ],
            "ticktext": [
                "0 %",
                "50 %",
                "100 %",
            ],
            "xanchor": "left",
        },
    }
    layout = {}
    layout.update(theme["layout"])
    layout.update(
        {
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "margin": {
                "t": 50,
                "b": 50,
                "l": 50,
            },
            "xaxis": {
                "ticks": "",
                "title": "Realizations",
                "showgrid": False,
                "side": "top",
            },
            "yaxis": {
                "ticks": "",
                "showticklabels": True,
                "tickmode": "array",
                "tickvals": list(status_df["JOB_ID"]),
                "ticktext": list(status_df["JOB"]),
                "showgrid": False,
                "automargin": True,
                "autorange": "reversed",
                "type": "category",
            },
            "height": max(350, len(status_df["JOB_ID"].unique()) * 15),
            "width": max(400, len(status_df["REAL"].unique()) * 12 + 250),
        }
    )

    return {"data": [data], "layout": layout}


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def render_parcoord(
    plot_df: pd.DataFrame,
    params: List[str],
    theme: dict,
    colormap: Union[List[str], List[list]],
    color_col: str,
    remove_constant: str,
    colormap_labels: Union[List[str], None] = None,
) -> dict:
    """Renders parallel coordinates plot"""
    # Create parcoords dimensions (one per parameter)
    dimentions_params = []
    if remove_constant == ["remove_constant"]:
        for param in params:
            if len(np.unique(plot_df[param].values)) > 1:
                dimentions_params.append(param)
    else:
        dimentions_params = params

    dimensions = [
        {"label": param, "values": plot_df[param].values.tolist()}
        for param in dimentions_params
    ]

    # Parcoords data dict
    data: dict = {
        "line": {
            "color": plot_df[color_col].values.tolist(),
            "colorscale": colormap,
            "showscale": True,
        },
        "dimensions": dimensions,
        "labelangle": -90,
        "labelside": "bottom",
        "type": "parcoords",
    }
    if color_col == "STATUS_BOOL":
        data["line"].update(
            {
                "cmin": -0.5,
                "cmax": 1.5,
                "colorbar": {
                    "tickvals": [0, 1],
                    "ticktext": colormap_labels,
                    "title": "Status",
                    "xanchor": "right",
                    "x": -0.02,
                    "len": 0.3,
                },
            },
        )
    else:
        data["line"].update(
            {
                "colorbar": {
                    "title": "Running time",
                    "xanchor": "right",
                    "x": -0.02,
                },
            },
        )

    layout = {}
    layout.update(theme["layout"])
    # Ensure sufficient spacing between each dimension and margin for labels
    width = len(dimensions) * 100 + 250
    margin_b = max([len(param) for param in params]) * 8
    layout.update({"width": width, "height": 800, "margin": {"b": margin_b, "t": 30}})

    return {"data": [data], "layout": layout}


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def make_colormap(color_array: list, discrete: int = None) -> list:
    """
    Returns a colormap:
    * If the `discrete` variable is set to an integer x, the colormap will be a discrete map of
    size x evenly sampled from the given color_array.
    * If discrete not defined or `None`: assumes continuous colormap and returns the given
    color_array.
    """
    if discrete is None:
        colormap = color_array
    else:
        colormap = []
        for i in range(0, discrete):
            colormap.append([i / discrete, color_array[i]])
            colormap.append([(i + 1) / discrete, color_array[i]])
    return colormap
