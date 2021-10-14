from typing import Any, Dict, List

import numpy as np
import pandas as pd

from ..types import FanchartOptions, StatisticsOptions
from ...._utils.fanchart_plotting import (
    get_fanchart_traces,
    FanchartData,
    FreeLineData,
    LowHighData,
    MinMaxData,
)
from ...._utils.statistics_plotting import (
    create_statistics_traces,
    StatisticsData,
    LineData,
)


def create_vector_realization_traces(
    ensemble_vectors_df: pd.DataFrame,
    vector: str,
    ensemble: str,
    color: str,
    line_shape: str,
    hovertemplate: str,
    show_legend: bool = True,
) -> List[dict]:
    """Renders line trace for each realization, includes history line if present"""
    return [
        {
            "line": {"shape": line_shape},
            "x": list(real_df["DATE"]),
            "y": list(real_df[vector]),
            "hovertemplate": f"{hovertemplate}Realization: {real}, Ensemble: {ensemble}",
            "name": ensemble,
            "legendgroup": ensemble,
            "marker": {"color": color},
            "showlegend": real_no == 0 and show_legend,
        }
        for real_no, (real, real_df) in enumerate(ensemble_vectors_df.groupby("REAL"))
    ]


# TODO: Rename to create_statistics_traces?
# pylint: disable=too-many-arguments, too-many-locals
def create_vector_statistics_traces(
    vector_statistics_df: pd.DataFrame,
    statistics_options: List[StatisticsOptions],
    color: str,
    legend_group: str,
    line_shape: str,
    refaxis: str = "DATE",
    hovertemplate: str = "(%{x}, %{y})<br>",
    show_legend: bool = True,
) -> List[Dict[str, Any]]:
    """Renders a statistical lines for each vector"""
    low_data = (
        LineData(
            data=vector_statistics_df[StatisticsOptions.P90].values,
            name=StatisticsOptions.P90.value,
        )
        if StatisticsOptions.P90 in statistics_options
        else None
    )
    mid_data = (
        LineData(
            data=vector_statistics_df[StatisticsOptions.P50].values,
            name=StatisticsOptions.P50.value,
        )
        if StatisticsOptions.P50 in statistics_options
        else None
    )
    high_data = (
        LineData(
            data=vector_statistics_df[StatisticsOptions.P10].values,
            name=StatisticsOptions.P10.value,
        )
        if StatisticsOptions.P10 in statistics_options
        else None
    )
    mean_data = (
        LineData(
            data=vector_statistics_df[StatisticsOptions.MEAN].values,
            name=StatisticsOptions.MEAN.value,
        )
        if StatisticsOptions.MEAN in statistics_options
        else None
    )
    minimum = (
        vector_statistics_df[StatisticsOptions.MIN].values
        if StatisticsOptions.MIN in statistics_options
        else None
    )
    maximum = (
        vector_statistics_df[StatisticsOptions.MAX].values
        if StatisticsOptions.MAX in statistics_options
        else None
    )

    data = StatisticsData(
        samples=vector_statistics_df["DATE"].values,
        free_line=mean_data,
        minimum=minimum,
        maximum=maximum,
        low=low_data,
        mid=mid_data,
        high=high_data,
    )
    return create_statistics_traces(
        data=data,
        color=color,
        legend_group=legend_group,
        line_shape=line_shape,
        show_legend=show_legend,
        hovertemplate=hovertemplate,
    )


# TODO: Rename to create_fanchart_traces?
def create_vector_fanchart_traces(
    vector_statistics_df: pd.DataFrame,
    color: str,
    legend_group: str,
    line_shape: str,
    fanchart_options: List[FanchartOptions],
    show_legend: bool = True,
    hovertemplate: str = "(%{x}, %{y})<br>",
) -> List[Dict[str, Any]]:
    """Get statistical fanchart traces for vector"""

    low_high_data = (
        LowHighData(
            low_data=vector_statistics_df[StatisticsOptions.P90].values,
            low_name="P90",
            high_data=vector_statistics_df[StatisticsOptions.P10].values,
            high_name="P10",
        )
        if FanchartOptions.P10_P90 in fanchart_options
        else None
    )
    minimum_maximum_data = (
        MinMaxData(
            minimum=vector_statistics_df[StatisticsOptions.MIN].values,
            maximum=vector_statistics_df[StatisticsOptions.MAX].values,
        )
        if FanchartOptions.MIN_MAX in fanchart_options
        else None
    )
    mean_data = (
        FreeLineData(
            "Mean",
            vector_statistics_df[StatisticsOptions.MEAN].values,
        )
        if FanchartOptions.MEAN in fanchart_options
        else None
    )

    data = FanchartData(
        samples=vector_statistics_df["DATE"].tolist(),
        low_high=low_high_data,
        minimum_maximum=minimum_maximum_data,
        free_line=mean_data,
    )
    return get_fanchart_traces(
        data=data,
        color=color,
        legend_group=legend_group,
        line_shape=line_shape,
        show_legend=show_legend,
        hovertemplate=hovertemplate,
    )


# TODO: Rename to create_history_vector_trace
def create_vector_history_trace(
    samples: list,
    history_data: np.ndarray,
    line_shape: str,
    show_legend: bool = False,
) -> dict:
    """Returns the history trace line"""
    if len(samples) != len(history_data):
        raise ValueError(f"Number of samples unequal number of data points!")

    return {
        "line": {"shape": line_shape},
        "x": samples,
        "y": history_data,
        "hovertext": "History",
        "hoverinfo": "y+x+text",
        "name": "History",
        "marker": {"color": "black"},
        "showlegend": show_legend,
        "legendgroup": "History",
    }
