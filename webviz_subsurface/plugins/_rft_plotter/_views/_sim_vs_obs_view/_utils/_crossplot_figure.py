from typing import List, Tuple

import numpy as np
import pandas as pd
import webviz_core_components as wcc

from ...._types import ColorAndSizeByType


def update_crossplot(
    df: pd.DataFrame, sizeby: ColorAndSizeByType, colorby: ColorAndSizeByType
) -> List[wcc.Graph]:

    sim_range = find_sim_range(df)
    sizeref, cmin, cmax = size_color_settings(df, sizeby, colorby)

    figures = []

    for _ens, ensdf in df.groupby("ENSEMBLE"):

        dframe = (
            ensdf.groupby(["WELL", "DATE", "ZONE", "TVD"]).mean().reset_index().copy()
        )
        trace = {
            "x": dframe["OBSERVED"],
            "y": dframe["SIMULATED"],
            "type": "scatter",
            "mode": "markers",
            "hovertext": [
                f"Well: {well}"
                f"<br>Zone: {zone}"
                f"<br>Pressure observation: {obs:.2f}"
                f"<br>Mean simulated pressure: {pressure:.2f}"
                f"<br>Mean misfit: {misfit:.2f}"
                f"<br>Stddev pressure: {stddev:.2f}"
                for well, zone, obs, stddev, misfit, pressure in zip(
                    dframe["WELL"],
                    dframe["ZONE"],
                    dframe["OBSERVED"],
                    dframe["STDDEV"],
                    dframe["DIFF"],
                    dframe["SIMULATED"],
                )
            ],
            "hoverinfo": "text",
            "marker": {
                "size": dframe[sizeby.value],
                "sizeref": 2.0 * sizeref / (30.0**2),
                "sizemode": "area",
                "sizemin": 6,
                "color": dframe[colorby.value],
                "cmin": cmin,
                "cmax": cmax,
                "colorscale": [[0, "#2584DE"], [1, "#E50000"]],
                "colorbar": {"x": 1.05},
                "showscale": True,
            },
        }

        layout = {
            "height": 400,
            "title": {
                "text": _ens,
                "y": 0.95,
                "x": 0.15,
                "xanchor": "center",
                "yanchor": "top",
            },
            "margin": {"l": 100, "r": 0, "b": 50, "t": 30},
            "showlegend": False,
            "xaxis": {
                "range": sim_range,
                "title": "Pressure Observation",
                "showticklabels": True,
            },
            "yaxis": {"range": sim_range, "title": "Simulated mean pressure"},
            "shapes": [
                {
                    "type": "line",
                    "x0": sim_range[0],
                    "y0": sim_range[0],
                    "x1": sim_range[1],
                    "y1": sim_range[1],
                    "line": {
                        "color": "#007079",
                        "width": 2,
                    },
                }
            ],
        }

        figures.append(wcc.Graph(figure={"data": [trace], "layout": layout}))
    return figures


def size_color_settings(
    df: pd.DataFrame, sizeby: ColorAndSizeByType, colorby: ColorAndSizeByType
) -> Tuple[np.float64, np.float64, np.float64]:

    df = df.groupby(["WELL", "DATE", "ZONE", "TVD", "ENSEMBLE"]).mean().reset_index()

    sizeref = df[sizeby.value].quantile(0.9)
    cmin = df[colorby.value].min()
    cmax = df[colorby.value].quantile(0.9)

    return sizeref, cmin, cmax


def find_sim_range(df: pd.DataFrame) -> List[np.float64]:

    df = df.groupby(["WELL", "DATE", "ZONE", "TVD", "ENSEMBLE"]).mean().reset_index()

    max_sim = (
        df["SIMULATED"].max()
        if df["SIMULATED"].max() > df["OBSERVED"].max()
        else df["OBSERVED"].max()
    )
    min_sim = (
        df["SIMULATED"].min()
        if df["SIMULATED"].min() < df["OBSERVED"].min()
        else df["OBSERVED"].min()
    )

    axis_extend = (max_sim - min_sim) * 0.1

    return [min_sim - axis_extend, max_sim + axis_extend]
