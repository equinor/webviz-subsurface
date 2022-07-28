import math
from typing import Any, Dict, List

import numpy as np
import pandas as pd


def _compare_dfs_obs(dframeobs: pd.DataFrame, ensembles: List) -> str:
    """Compare obs and obs_error values for ensembles.
    Return info text if not equal"""

    text = ""
    if len(ensembles) > 1:
        ens1 = ensembles[0]
        obs1 = dframeobs[dframeobs.ENSEMBLE.eq(ens1)].obs
        obserr1 = dframeobs[dframeobs.ENSEMBLE.eq(ens1)].obs_error
        for idx in range(1, len(ensembles)):
            ens = ensembles[idx]
            obs = dframeobs[dframeobs.ENSEMBLE.eq(ens)].obs
            obserr = dframeobs[dframeobs.ENSEMBLE.eq(ens)].obs_error

            if not obs1.equals(obs):
                text = (
                    text + "\n--WARNING-- " + ens + " obs data is different to " + ens1
                )
            else:
                text = text + "\n" + "✅ " + ens + " obs data is equal to " + ens1

            if not obserr1.equals(obserr):
                text = (
                    text
                    + "\n--WARNING-- "
                    + ens
                    + " obs error data is different to "
                    + ens1
                )
            else:
                text = text + "\n" + "✅ " + ens + " obs error data is equal to " + ens1

    return text


def get_unique_column_values(df: pd.DataFrame, colname: str) -> List:
    """return dataframe column values. If no matching colname, return [999].
    Currently unused. Consider removing"""
    if colname in df:
        values = df[colname].unique()
        values = sorted(values)
    else:
        values = [999]
    return values


def find_max_diff(df: pd.DataFrame) -> np.float64:
    max_diff = np.float64(0)
    for _ens, ensdf in df.groupby("ENSEMBLE"):
        realdf = ensdf.groupby("REAL").sum().reset_index()
        max_diff = (
            max_diff if max_diff > realdf["ABSDIFF"].max() else realdf["ABSDIFF"].max()
        )
    return max_diff


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
    decimals = 1
    if mean_value < 0.001:
        decimals = 5
    elif mean_value < 0.01:
        decimals = 4
    elif mean_value < 0.1:
        decimals = 3
    elif mean_value < 10:
        decimals = 2
    return {
        "x": 0.2,
        "y": mean_value,
        "xref": "paper",
        "yref": yref,
        "text": f"Average: {mean_value:.{decimals}f}",
        "showarrow": True,
        "align": "center",
        "arrowhead": 2,
        "arrowsize": 1,
        "arrowwidth": 1,
        "arrowcolor": "#636363",
        "ax": 20,
        "ay": -25,
    }


def _map_initial_marker_size(total_data_points: int, no_ens: int) -> int:
    """Calculate marker size based on number of datapoints per ensemble"""
    if total_data_points < 1:
        raise ValueError(
            "No data points found. Something is wrong with your input data."
            f"Value of total_data_points is {total_data_points}"
        )
    data_points_per_ens = int(total_data_points / no_ens)
    marker_size = int(550 / math.sqrt(data_points_per_ens))
    if marker_size > 30:
        marker_size = 30
    elif marker_size < 2:
        marker_size = 2
    return marker_size
