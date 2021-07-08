from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

import numpy as np

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
    low     - List of low percentile value data. Type: float
    high    - List of high percentile value data. Type: float
    minimum - List of minimum value data. Type: float
    """

    # TODO: Ensure correct typehints
    samples: list = field(default_factory=list)
    mean: Optional[np.ndarray] = None
    maximum: Optional[np.ndarray] = None
    low: Optional[np.ndarray] = None
    high: Optional[np.ndarray] = None
    minimum: Optional[np.ndarray] = None


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
    if data.mean and len(data.samples) != len(data.mean):
        raise ValueError(
            f"Invalid fanchart mean value data length. len(data.samples) != len(data.mean)"
        )
    if data.maximum and len(data.samples) != len(data.maximum):
        raise ValueError(
            f"Invalid fanchart maximum value data length. len(data.samples) != len(data.maximum)"
        )
    if data.low and len(data.samples) != len(data.low):
        raise ValueError(
            f"Invalid fanchart low percentile value data length. len(data.samples) != len(data.low)"
        )
    if data.high and len(data.samples) != len(data.high):
        raise ValueError(
            f"Invalid fanchart high percentile value data length. len(data.samples) != len(data.high)"
        )
    if data.minimum and len(data.samples) != len(data.minimum):
        raise ValueError(
            f"Invalid fanchart minimum value data length. len(data.samples) != len(data.minimum)"
        )


# TODO: Check if hovertemplate is preferred instead of hovertext. Simulation timeseries used hovertemplate
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

    Takes 'data' with data for each statistical feature as input, and creates a list of traces for each feature.
    Plotly plots traces from front to end of the list, thereby the last trace is plotted on top.

    Provides a list of traces: [trace0, tract1, ..., traceN]

    Fanchart is created by use of fill "tonexty" configuration for the traces. Fill "tonexty" is missleading naming,
    as "tonexty" in trace1 fills to y in trace0, i.e y in previous trace.

    The order of traces are minimum, low, high, maximum and mean. Thus it is required that values in minimum <= values
    in low, and low <= high, and high <= maximum. Fill is setting "tonexty" in this function is set s.t. trace fillings
    are not stacked making colors in fills unchanged when disabling trace for one or more of statistics inputs
    (minimum, low, high or maximum).

    Mean is last trace and is plotted on top as a line - without filling to other traces.

    Note:
    Assume values: minimum <= low, low <= high and high <= maximum due to fill setting "tonexty".

    Returns:
    List of fanchart traces, one for each statistical feature in data input - [trace0, tract1, ..., traceN].
    """

    # validate_fanchart_data(data)

    fill_color_light = hex_to_rgba(color, 0.3)
    fill_color_dark = hex_to_rgba(color, 0.6)
    line_color = hex_to_rgba(color, 1)

    traces: List[Dict[str, Any]] = []

    if data.minimum is not None:
        traces.append(
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
            }
        )

    if data.low is not None:
        low_trace = {
            "name": legend_group,
            "hovertext": "Low percentile " + hovertext,
            "x": data.samples if direction == TraceDirection.HORIZONTAL else data.low,
            "y": data.low if direction == TraceDirection.HORIZONTAL else data.samples,
            "xaxis": xaxis,
            "yaxis": yaxis,
            "mode": "lines",
            "line": {"width": 0, "color": line_color, "shape": line_shape},
            "legendgroup": legend_group,
            "showlegend": False,
        }
        # Add fill if not first element
        if len(traces) > 0:
            low_trace["fill"] = "tonexty"
            low_trace["fillcolor"] = fill_color_light
        traces.append(low_trace)

    if data.high is not None:
        high_trace = {
            "name": legend_group,
            "hovertext": "High percentile " + hovertext,
            "x": data.samples if direction == TraceDirection.HORIZONTAL else data.high,
            "y": data.high if direction == TraceDirection.HORIZONTAL else data.samples,
            "xaxis": xaxis,
            "yaxis": yaxis,
            "mode": "lines",
            "line": {"width": 0, "color": line_color, "shape": line_shape},
            "legendgroup": legend_group,
            "showlegend": False,
        }
        # Add fill if not first element
        if len(traces) > 0:
            high_trace["fill"] = "tonexty"
            high_trace["fillcolor"] = fill_color_dark
        traces.append(high_trace)

    if data.maximum is not None:
        maximum_trace = {
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
            "line": {"width": 0, "color": line_color, "shape": line_shape},
            "legendgroup": legend_group,
            "showlegend": False,
        }
        # Add fill if not first element
        if len(traces) > 0:
            fill_color = (
                fill_color_dark
                if "fillcolor" in traces[-1].keys()
                and traces[-1]["fillcolor"] == fill_color_light
                else fill_color_light
            )
            maximum_trace["fill"] = "tonexty"
            maximum_trace["fillcolor"] = fill_color
        traces.append(maximum_trace)

    if data.mean is not None:
        traces.append(
            {
                "name": legend_group,
                "hovertext": "Mean " + hovertext,
                "x": data.samples
                if direction == TraceDirection.HORIZONTAL
                else data.mean,
                "y": data.mean
                if direction == TraceDirection.HORIZONTAL
                else data.samples,
                "xaxis": xaxis,
                "yaxis": yaxis,
                "mode": "lines",
                "line": {"color": line_color, "shape": line_shape},
                "legendgroup": legend_group,
                "showlegend": show_legend,
            }
        )

    return traces
