import warnings
from typing import Optional

import pandas as pd
import numpy as np


def set_simulation_line_shape_fallback(line_shape_fallback: str) -> str:
    """
    Defines a Plotly line_shape to use if a vector is not thought to be a rate or a total.
    """
    line_shape_fallback = line_shape_fallback.lower()
    if line_shape_fallback in ("backfilled", "backfill"):
        return "vh"
    if line_shape_fallback in ["hv", "vh", "hvh", "vhv", "spline", "linear"]:
        return line_shape_fallback
    warnings.warn(
        f"{line_shape_fallback}, is not a valid line_shape option, will use linear."
    )
    return "linear"


def get_simulation_line_shape(
    line_shape_fallback: str, vector: str, smry_meta: Optional[pd.DataFrame] = None
) -> str:
    """Get simulation time series line shape, smry_meta is a pd.DataFrame on the format given
    by `load_smry_meta` in `../_datainput/fmu_input.py`.
    """

    if smry_meta is None:
        return line_shape_fallback
    try:
        if smry_meta.is_rate[vector]:
            return "vh"
        if smry_meta.is_total[vector]:
            return "linear"
    except (AttributeError, KeyError):
        pass
    return line_shape_fallback


def calc_series_statistics(df: pd.DataFrame, vectors: list, refaxis: str = "DATE"):
    """Calculate statistics for given vectors over the ensembles
    refaxis is used if another column than DATE should be used to groupby.
    """
    # Invert p10 and p90 due to oil industry convention.
    def p10(x):
        return np.nanpercentile(x, q=90)

    def p90(x):
        return np.nanpercentile(x, q=10)

    # Calculate statistics, ignoring NaNs.
    stat_df = (
        df[["ENSEMBLE", refaxis] + vectors]
        .groupby(["ENSEMBLE", refaxis])
        .agg([np.nanmean, np.nanmin, np.nanmax, p10, p90])
        .reset_index(level=["ENSEMBLE", refaxis], col_level=1)
    )
    # Rename nanmin, nanmax and nanmean to min, max and mean.
    col_stat_label_map = {
        "nanmin": "min",
        "nanmax": "max",
        "nanmean": "mean",
        "p10": "high_p10",
        "p90": "low_p90",
    }
    stat_df.rename(columns=col_stat_label_map, level=1, inplace=True)

    return stat_df


def add_fanchart_traces(
    ens_stat_df: pd.DataFrame,
    vector: str,
    color: str,
    legend_group: str,
    line_shape: str,
    refaxis: str = "DATE",
):
    """Renders a fanchart for an ensemble vector"""

    fill_color = hex_to_rgb(color, 0.3)
    line_color = hex_to_rgb(color, 1)
    return [
        {
            "name": legend_group,
            "hovertext": "Maximum",
            "x": ens_stat_df[("", refaxis)],
            "y": ens_stat_df[(vector, "max")],
            "mode": "lines",
            "line": {"width": 0, "color": line_color, "shape": line_shape},
            "legendgroup": legend_group,
            "showlegend": False,
        },
        {
            "name": legend_group,
            "hovertext": "P90",
            "x": ens_stat_df[("", refaxis)],
            "y": ens_stat_df[(vector, "low_p90")],
            "mode": "lines",
            "fill": "tonexty",
            "fillcolor": fill_color,
            "line": {"width": 0, "color": line_color, "shape": line_shape},
            "legendgroup": legend_group,
            "showlegend": False,
        },
        {
            "name": legend_group,
            "hovertext": "P10",
            "x": ens_stat_df[("", refaxis)],
            "y": ens_stat_df[(vector, "high_p10")],
            "mode": "lines",
            "fill": "tonexty",
            "fillcolor": fill_color,
            "line": {"width": 0, "color": line_color, "shape": line_shape},
            "legendgroup": legend_group,
            "showlegend": False,
        },
        {
            "name": legend_group,
            "hovertext": "Mean",
            "x": ens_stat_df[("", refaxis)],
            "y": ens_stat_df[(vector, "mean")],
            "mode": "lines",
            "fill": "tonexty",
            "fillcolor": fill_color,
            "line": {"color": line_color, "shape": line_shape},
            "legendgroup": legend_group,
            "showlegend": True,
        },
        {
            "name": legend_group,
            "hovertext": "Minimum",
            "x": ens_stat_df[("", refaxis)],
            "y": ens_stat_df[(vector, "min")],
            "mode": "lines",
            "fill": "tonexty",
            "fillcolor": fill_color,
            "line": {"width": 0, "color": line_color, "shape": line_shape},
            "legendgroup": legend_group,
            "showlegend": False,
        },
    ]


def hex_to_rgb(hex_string, opacity=1):
    """Converts a hex color to rgb"""
    hex_string = hex_string.lstrip("#")
    hlen = len(hex_string)
    rgb = [int(hex_string[i : i + hlen // 3], 16) for i in range(0, hlen, hlen // 3)]
    rgb.append(opacity)
    return f"rgba{tuple(rgb)}"
