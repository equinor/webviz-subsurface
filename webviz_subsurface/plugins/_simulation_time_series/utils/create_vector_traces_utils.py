from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from webviz_subsurface._providers import Frequency
from webviz_subsurface._utils.fanchart_plotting import (
    FanchartData,
    FreeLineData,
    LowHighData,
    MinMaxData,
    get_fanchart_traces,
)
from webviz_subsurface._utils.statistics_plotting import (
    LineData,
    StatisticsData,
    create_statistics_traces,
)

from ..types import FanchartOptions, StatisticsOptions
from ..utils.from_timeseries_cumulatives import is_per_interval_or_per_day_vector


def create_vector_observation_traces(
    vector_observations: dict,
    color: str = "black",
    legend_group: Optional[str] = None,
    show_legend: bool = False,
) -> List[dict]:
    """Create list of observations traces from vector observations

    `Input:`
    * vector_observations: dict - Dictionary with observation data for a vector
    * color: str - Color of observation traces for vector
    * legend_group: Optional[str] - Overwrite default legend group. Name of legend group, added as
    legend group and name if provided.
    * show_legend: bool - Show legend status for traces


    `Return:`
    List of marker traces for each observation for vector
    """
    observation_traces: List[dict] = []

    _name = "Observation" if legend_group is None else "Observation: " + legend_group
    _legend_group = "Observation" if legend_group is None else legend_group

    for observation in vector_observations.get("observations", []):
        hovertext = observation.get("comment")
        hovertemplate = (
            "(%{x}, %{y})<br>" + hovertext if hovertext else "(%{x}, %{y})<br>"
        )
        observation_traces.append(
            {
                "name": _name,
                "legendgroup": _legend_group,
                "x": [observation.get("date"), []],
                "y": [observation.get("value"), []],
                "marker": {"color": color},
                "hovertemplate": hovertemplate,
                "showlegend": show_legend,
                "error_y": {
                    "type": "data",
                    "array": [observation.get("error"), []],
                    "visible": True,
                },
            }
        )
    return observation_traces


def create_vector_realization_traces(
    vector_df: pd.DataFrame,
    ensemble: str,
    color: str,
    legend_group: str,
    line_shape: str,
    hovertemplate: str,
    show_legend: bool = False,
    legendrank: Optional[int] = None,
) -> List[dict]:
    """Renders line trace for each realization, includes history line if present

    `Input:`
    * vector_df: pd.DataFrame - Dataframe with vector data with following columns:\n
    ["DATE", "REAL", vector]

    * ensemble: str - Name of ensemble
    * color: str - color for traces
    * legend_group: str - legend group owner
    * line_shape: str - specified line shape for trace
    * show_legend: bool - show legend when true, otherwise do not show
    * hovertemplate: str - template for hovering of data points in trace lines
    * legendrank: int - rank value for legend in figure
    """
    vector_names = list(set(vector_df.columns) ^ set(["DATE", "REAL"]))
    if len(vector_names) != 1:
        raise ValueError(
            f"Expected one vector column present in dataframe, got {len(vector_names)}!"
        )

    vector_name = vector_names[0]
    return [
        {
            "line": {"width": 1, "shape": line_shape},
            "x": list(real_df["DATE"]),
            "y": list(real_df[vector_name]),
            "hovertemplate": f"{hovertemplate}Realization: {real}, Ensemble: {ensemble}",
            "name": legend_group,
            "legendgroup": legend_group,
            "marker": {"color": color},
            "legendrank": legendrank,
            "showlegend": real_no == 0 and show_legend,
        }
        for real_no, (real, real_df) in enumerate(vector_df.groupby("REAL"))
    ]


def validate_vector_statistics_df_columns(
    vector_statistics_df: pd.DataFrame,
) -> None:
    """Validate columns of vector statistics DataFrame

    Verify DataFrame columns: ["DATE", MEAN, MIN, MAX, P10, P90, P50]

    Raise value error if columns are not matching

    `Input:`
    * vector_statistics_df: pd.Dataframe - Dataframe with dates and vector statistics columns.
    """
    expected_columns = [
        "DATE",
        StatisticsOptions.MEAN,
        StatisticsOptions.MIN,
        StatisticsOptions.MAX,
        StatisticsOptions.P10,
        StatisticsOptions.P90,
        StatisticsOptions.P50,
    ]
    if list(vector_statistics_df.columns) != expected_columns:
        raise ValueError(
            f"Incorrect dataframe columns, expected {expected_columns}, got "
            f"{vector_statistics_df.columns}"
        )


# pylint: disable = too-many-arguments, too-many-locals
def create_vector_statistics_traces(
    vector_statistics_df: pd.DataFrame,
    statistics_options: List[StatisticsOptions],
    color: str,
    legend_group: str,
    line_shape: str,
    line_width: int = 2,
    hovertemplate: str = "(%{x}, %{y})<br>",
    show_legend: bool = False,
    legendrank: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Get statistical lines for provided vector statistics DataFrame.

    `Input:`
    * vector_statistics_df: pd.Dataframe - Dataframe with dates and statistics columns
    for specific vector:\n
        DataFrame columns: ["DATE", MEAN, MIN, MAX, P10, P90, P50]

    * statistics_options: List[StatisticsOptions] - List of statistic options to include
    * color: str - color for traces
    * legend_group: str - legend group owner
    * line_shape: str - specified line shape for traces
    * line_width: str - specified line width for traces
    * hovertemplate: str - template for hovering of data points in trace lines
    * show_legend: bool - show legend when true, otherwise do not show
    * legendrank: int - rank value for legend in figure
    """
    # Validate columns format
    validate_vector_statistics_df_columns(vector_statistics_df)

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
        line_width=line_width,
        show_legend=show_legend,
        hovertemplate=hovertemplate,
        legendrank=legendrank,
    )


def create_vector_fanchart_traces(
    vector_statistics_df: pd.DataFrame,
    fanchart_options: List[FanchartOptions],
    hex_color: str,
    legend_group: str,
    line_shape: str,
    hovertemplate: str = "(%{x}, %{y})<br>",
    show_legend: bool = False,
    legendrank: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Get statistical fanchart traces for provided vector statistics DataFrame.

    `Input:`
    * vector_statistics_df: pd.Dataframe - Dataframe with dates and statistics columns
    for specific vector:\n
        DataFrame columns: ["DATE", MEAN, MIN, MAX, P10, P90, P50]

    * fanchart_options: List[FanchartOptions] - List of fanchart options to include
    * hex_color: str - Hex color for traces and fill
    * legend_group: str - legend group owner
    * line_shape: str - specified line shape for trace
    * hovertemplate: str - template for hovering of data points in trace lines
    * show_legend: bool - show legend when true, otherwise do not show
    * legendrank: int - rank value for legend in figure
    """
    # Validate columns format
    validate_vector_statistics_df_columns(vector_statistics_df)

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
        hex_color=hex_color,
        legend_group=legend_group,
        line_shape=line_shape,
        show_legend=show_legend,
        hovertemplate=hovertemplate,
        legendrank=legendrank,
    )


def create_history_vector_trace(
    samples: list,
    history_data: np.ndarray,
    line_shape: str,
    color: str = "black",
    vector_name: Optional[str] = None,
    show_legend: bool = False,
    legendrank: Optional[int] = None,
) -> dict:
    """Returns the history data as trace line

    `Input:`
    * samples: list - list of samples
    * history_data: np.ndarray - 1D np.array of history data
    * line_shape: str - specified line shape
    * color: str - line color
    * vector_name: Optional[str] - Name of vector, appended to hovertext if provided
    * show_legend: bool - show legend when true, otherwise do not show

    `Return:`
    Trace line for provided history data. Raise value error if number of samples
    and number of history data points does not match.
    """
    if len(samples) != len(history_data):
        raise ValueError("Number of samples unequal number of data points!")

    hovertext = "History" if vector_name is None else "History: " + vector_name

    return {
        "line": {"shape": line_shape},
        "x": samples,
        "y": history_data,
        "hovertext": hovertext,
        "hoverinfo": "y+x+text",
        "name": "History",
        "marker": {"color": color},
        "showlegend": show_legend,
        "legendgroup": "History",
        "legendrank": legendrank,
    }


def render_hovertemplate(vector: str, sampling_frequency: Optional[Frequency]) -> str:
    """Based on render_hovertemplate(vector: str, interval: Optional[str]) in
    webviz_subsurface/_utils/simulation_timeseries.py

    Adjusted to use Frequency enum and handle "Raw" and "weekly" frequency.

    `Input:`
    * vector: str - name of vector
    * sampling_frequency: Optional[Frequency] - sampling frequency for hovering data info
    """
    if is_per_interval_or_per_day_vector(vector) and sampling_frequency:
        if sampling_frequency in [Frequency.DAILY, Frequency.WEEKLY]:
            return "(%{x|%b} %{x|%-d}, %{x|%Y}, %{y})<br>"
        if sampling_frequency == Frequency.MONTHLY:
            return "(%{x|%b} %{x|%Y}, %{y})<br>"
        if sampling_frequency == Frequency.QUARTERLY:
            return "(Q%{x|%q} %{x|%Y}, %{y})<br>"
        if sampling_frequency == Frequency.YEARLY:
            return "(%{x|%Y}, %{y})<br>"
        raise ValueError(f"Interval {sampling_frequency.value} is not supported.")
    return "(%{x}, %{y})<br>"  # Plotly's default behavior
