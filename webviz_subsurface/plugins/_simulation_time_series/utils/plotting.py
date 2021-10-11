from typing import Any, Dict, List

import pandas as pd

from ..types import FanchartOptions, StatisticsOptions
from ...._utils.fanchart_plotting import (
    get_fanchart_traces,
    FanchartData,
    FreeLineData,
    LowHighData,
    MinMaxData,
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


# pylint: disable=too-many-arguments
# TODO: Possible to refactor? Make utility as for fanchart?
def create_vector_statistics_traces(
    ensemble_vector_statistic_df: pd.DataFrame,
    vector: str,
    statistics_options: List[StatisticsOptions],
    color: str,
    legend_group: str,
    line_shape: str,
    refaxis: str = "DATE",
    hovertemplate: str = "(%{x}, %{y})<br>",
    show_legend: bool = True,
) -> List[Dict[str, Any]]:
    """Renders a statistical lines for each vector"""
    traces = []
    for i, option in enumerate(statistics_options):
        if option == StatisticsOptions.MEAN:
            traces.append(
                {
                    "name": legend_group,
                    "hovertemplate": hovertemplate + "Mean",
                    "x": ensemble_vector_statistic_df[("", refaxis)],
                    "y": ensemble_vector_statistic_df[(vector, "mean")],
                    "mode": "lines",
                    "line": {"color": color, "shape": line_shape, "width": 3},
                    "legendgroup": legend_group,
                    "showlegend": i == 0 and show_legend,
                }
            )
        if option == StatisticsOptions.P10:
            traces.append(
                {
                    "name": legend_group,
                    "hovertemplate": hovertemplate + "P10",
                    "x": ensemble_vector_statistic_df[("", refaxis)],
                    "y": ensemble_vector_statistic_df[(vector, "high_p10")],
                    "mode": "lines",
                    "line": {"color": color, "shape": line_shape, "dash": "dashdot"},
                    "legendgroup": legend_group,
                    "showlegend": i == 0 and show_legend,
                }
            )
        if option == StatisticsOptions.P90:
            traces.append(
                {
                    "name": legend_group,
                    "hovertemplate": hovertemplate + "P90",
                    "x": ensemble_vector_statistic_df[("", refaxis)],
                    "y": ensemble_vector_statistic_df[(vector, "low_p90")],
                    "mode": "lines",
                    "line": {"color": color, "shape": line_shape, "dash": "dashdot"},
                    "legendgroup": legend_group,
                    "showlegend": i == 0 and show_legend,
                }
            )
        if option == StatisticsOptions.P50:
            traces.append(
                {
                    "name": legend_group,
                    "hovertemplate": hovertemplate + "P50",
                    "x": ensemble_vector_statistic_df[("", refaxis)],
                    "y": ensemble_vector_statistic_df[(vector, "p50")],
                    "mode": "lines",
                    "line": {
                        "color": color,
                        "shape": line_shape,
                        "dash": "dot",
                        "width": 3,
                    },
                    "legendgroup": legend_group,
                    "showlegend": i == 0 and show_legend,
                }
            )
        if option == StatisticsOptions.MAX:
            traces.append(
                {
                    "name": legend_group,
                    "hovertemplate": hovertemplate + "Maximum",
                    "x": ensemble_vector_statistic_df[("", refaxis)],
                    "y": ensemble_vector_statistic_df[(vector, "max")],
                    "mode": "lines",
                    "line": {
                        "color": color,
                        "shape": line_shape,
                        "dash": "longdash",
                        "width": 1.5,
                    },
                    "legendgroup": legend_group,
                    "showlegend": i == 0 and show_legend,
                }
            )
        if option == StatisticsOptions.MIN:
            traces.append(
                {
                    "name": legend_group,
                    "hovertemplate": hovertemplate + "Minimum",
                    "x": ensemble_vector_statistic_df[("", refaxis)],
                    "y": ensemble_vector_statistic_df[(vector, "min")],
                    "mode": "lines",
                    "line": {
                        "color": color,
                        "shape": line_shape,
                        "dash": "longdash",
                        "width": 1.5,
                    },
                    "legendgroup": legend_group,
                    "showlegend": i == 0 and show_legend,
                }
            )
    return traces


def create_vector_fanchart_traces(
    ensemble_vector_statistic_df: pd.DataFrame,
    vector: str,
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
            low_data=ensemble_vector_statistic_df[(vector, "low_p90")].values,
            low_name="P90",
            high_data=ensemble_vector_statistic_df[(vector, "high_p10")].values,
            high_name="P10",
        )
        if FanchartOptions.P10_P90 in fanchart_options
        else None
    )
    minimum_maximum_data = (
        MinMaxData(
            minimum=ensemble_vector_statistic_df[(vector, "min")].values,
            maximum=ensemble_vector_statistic_df[(vector, "max")].values,
        )
        if FanchartOptions.MIN_MAX in fanchart_options
        else None
    )
    mean_data = (
        FreeLineData("Mean", ensemble_vector_statistic_df[(vector, "mean")].values)
        if FanchartOptions.MEAN in fanchart_options
        else None
    )

    data = FanchartData(
        samples=ensemble_vector_statistic_df[("", "DATE")].tolist(),
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


def create_vector_history_trace(
    history_vectors_df: pd.DataFrame,
    vector: str,
    line_shape: str,
    show_legend: bool = False,
) -> dict:
    """Returns the history trace line"""
    return {
        "line": {"shape": line_shape},
        "x": history_vectors_df["DATE"],
        "y": history_vectors_df[vector],
        "hovertext": "History",
        "hoverinfo": "y+x+text",
        "name": "History",
        "marker": {"color": "black"},
        "showlegend": show_legend,
        "legendgroup": "History",
    }
