from typing import Any, Dict, List
from dataclasses import dataclass, field

import pandas as pd
from enum import Enum

from .colors import hex_to_rgba


@dataclass
class FanchartData:
    """
    Dataclass defining fanchart data utilized in creation of statistical fanchart traces

    Attributes:
    samples - Common sample point list for each following value list.
    mean    - List of mean value data. Type: float
    maximum - List of maximum value data. Type: float
    p90     - List of p90 value data. Type: float
    p10     - List of p10 value data. Type: float
    minimum - List of minimum value data. Type: float
    """

    # TODO: Ensure correct typehints
    samples: list = field(default_factory=list)
    mean: List[float] = field(default_factory=list)
    maximum: List[float] = field(default_factory=list)
    p90: List[float] = field(default_factory=list)
    p10: List[float] = field(default_factory=list)
    minimum: List[float] = field(default_factory=list)


class TraceDirection(Enum):
    HORIZONTAL = 1
    VERTICAL = 2


def validate_fanchart_data(data: FanchartData) -> None:
    """
    Validation of fanchart data

    Ensure equal length of all statistical fanchart data lists and x-axis data list

    Raise ValueError if lengths are unequal
    """
    if len(data.samples) <= 0:
        raise ValueError("Empty x-axis data list in FanchartData")
    if len(data.samples) != len(data.mean):
        raise ValueError(
            f"Invalid fanchart mean value data length. len(data.samples) != len(data.mean)"
        )
    if len(data.samples) != len(data.maximum):
        raise ValueError(
            f"Invalid fanchart maximum value data length. len(data.samples) != len(data.maximum)"
        )
    if len(data.samples) != len(data.p90):
        raise ValueError(
            f"Invalid fanchart p90 value data length. len(data.samples) != len(data.p90)"
        )
    if len(data.samples) != len(data.p10):
        raise ValueError(
            f"Invalid fanchart p10 value data length. len(data.samples) != len(data.p10)"
        )
    if len(data.samples) != len(data.minimum):
        raise ValueError(
            f"Invalid fanchart minimum value data length. len(data.samples) != len(data.minimum)"
        )


# TODO: Check if hovertemplate is preferred instead of hovertext. Simulation timeseries used hovertemplate
# TODO: Fix fillcolor or similar for mean data legend?
def get_fanchart_traces(
    data: FanchartData,
    color: str,
    legend_group: str,
    line_shape: str = "linear",
    xaxis: str = "x",
    yaxis: str = "y",
    hovertext: str = "",
    show_legend: bool = True,
    direction: TraceDirection = TraceDirection.HORIZONTAL,
) -> List[Dict[str, Any]]:
    """
    Utility function for creating statistical fanchart traces


    Note: Assumes p10 and p90 between minimum and maximum values.

    Returns:
    List of fanchart traces. One trace for each of the statistical feature in FanchartData
    """

    validate_fanchart_data(data)

    fill_color_min_max = hex_to_rgba(color, 0.3)
    fill_color_p10_p90 = hex_to_rgba(color, 0.5)
    line_color = hex_to_rgba(color, 1)

    # [trace0, tract1,...,traceN]
    # Traces are plotted first from list, thus last trace i plotted on top.
    # Fill "tonexty" is missleading naming, "tonexty" in trace1 fills to y in trace0, and
    # "tonexty" in trace3 fills to y in trace2
    return [
        {
            "name": legend_group,
            "hovertext": "Minimum " + hovertext,
            "x": data.samples
            if direction == TraceDirection.HORIZONTAL
            else data.minimum,
            "y": data.minimum
            if direction == TraceDirection.HORIZONTAL
            else data.samples,
            "xaxis": xaxis,
            "yaxis": yaxis,
            "mode": "lines",
            "line": {"width": 0, "color": line_color, "shape": line_shape},
            "legendgroup": legend_group,
            "showlegend": False,
        },
        {
            "name": legend_group,
            "hovertext": "Maximum " + hovertext,
            "x": data.samples
            if direction == TraceDirection.HORIZONTAL
            else data.maximum,
            "y": data.maximum
            if direction == TraceDirection.HORIZONTAL
            else data.samples,
            "xaxis": xaxis,
            "yaxis": yaxis,
            "mode": "lines",
            "fill": "tonexty",
            "fillcolor": fill_color_min_max,
            "line": {"width": 0, "color": line_color, "shape": line_shape},
            "legendgroup": legend_group,
            "showlegend": False,
        },
        {
            "name": legend_group,
            "hovertext": "P10 " + hovertext,
            "x": data.samples if direction == TraceDirection.HORIZONTAL else data.p10,
            "y": data.p10 if direction == TraceDirection.HORIZONTAL else data.samples,
            "xaxis": xaxis,
            "yaxis": yaxis,
            "mode": "lines",
            "line": {"width": 0, "color": line_color, "shape": line_shape},
            "legendgroup": legend_group,
            "showlegend": False,
        },
        {
            "name": legend_group,
            "hovertext": "P90 " + hovertext,
            "x": data.samples if direction == TraceDirection.HORIZONTAL else data.p90,
            "y": data.p90 if direction == TraceDirection.HORIZONTAL else data.samples,
            "xaxis": xaxis,
            "yaxis": yaxis,
            "mode": "lines",
            "fill": "tonexty",
            "fillcolor": fill_color_p10_p90,
            "line": {"width": 0, "color": line_color, "shape": line_shape},
            "legendgroup": legend_group,
            "showlegend": False,
        },
        {
            "name": legend_group,
            "hovertext": "Mean " + hovertext,
            "x": data.samples if direction == TraceDirection.HORIZONTAL else data.mean,
            "y": data.mean if direction == TraceDirection.HORIZONTAL else data.samples,
            "xaxis": xaxis,
            "yaxis": yaxis,
            "mode": "lines",
            "line": {"color": line_color, "shape": line_shape},
            "legendgroup": legend_group,
            "showlegend": show_legend,
        },
    ]
