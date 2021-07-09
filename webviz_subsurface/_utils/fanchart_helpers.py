from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from .colors import hex_to_rgba


@dataclass
class FanchartData:
    """
    Dataclass defining fanchart data utilized in creation of statistical fanchart traces

    Attributes:
    samples - Common sample point list for each following value list.
    mean    - 1D np.array of mean value data.
    maximum - 1D np.array of maximum value data.
    low     - 1D np.array of low percentile value data.
    high    - 1D np.array of high percentile value data.
    minimum - 1D np.array of minimum value data.
    """

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
    if data.mean is not None and len(data.samples) != len(data.mean):
        raise ValueError(
            "Invalid fanchart mean value data length. len(data.samples) != len(data.mean)"
        )
    if data.maximum is not None and len(data.samples) != len(data.maximum):
        raise ValueError(
            "Invalid fanchart maximum value data length. len(data.samples) != len(data.maximum)"
        )
    if data.low is not None and len(data.samples) != len(data.low):
        raise ValueError(
            "Invalid fanchart low percentile value data length. len(data.samples) != len(data.low)"
        )
    if data.high is not None and len(data.samples) != len(data.high):
        raise ValueError(
            "Invalid fanchart high percentile value data length. len(data.samples) != len(data.high)"
        )
    if data.minimum is not None and len(data.samples) != len(data.minimum):
        raise ValueError(
            "Invalid fanchart minimum value data length. len(data.samples) != len(data.minimum)"
        )


# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
def get_fanchart_traces(
    data: FanchartData,
    color: str,
    legend_group: str,
    line_shape: str = "linear",
    xaxis: str = "x",
    yaxis: str = "y",
    low_percentile_name: str = "P90",
    high_percentile_name: str = "P10",
    show_legend: bool = True,
    direction: TraceDirection = TraceDirection.HORIZONTAL,
    hovertext: str = "",
    hovertemplate: Optional[str] = None,
    hovermode: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Utility function for creating statistical fanchart traces

    Takes 'data' with data for each statistical feature as input, and creates a list of traces for
    each feature. Plotly plots traces from front to end of the list, thereby the last trace is
    plotted on top.

    Provides a list of traces: [trace0, tract1, ..., traceN]

    Fanchart is created by use of fill "tonexty" configuration for the traces. Fill "tonexty" is
    missleading naming, as "tonexty" in trace1 fills to y in trace0, i.e y in previous trace.

    The order of traces are minimum, low, high, maximum and mean. Thus it is required that values
    in minimum <= values in low, and low <= high, and high <= maximum. Fill is setting "tonexty"
    in this function is set s.t. trace fillings are not stacked making colors in fills unchanged
    when disabling trace for one or more of statistics inputs (minimum, low, high or maximum).

    Mean is last trace and is plotted on top as a line - without filling to other traces.

    Note:
    Assume values: minimum <= low, low <= high and high <= maximum due to fill setting "tonexty".
    If hovertemplate is proved it overrides the hovertext

    Returns:
    List of fanchart traces, one for each statistical feature in data input.
    [trace0, tract1, ..., traceN].
    """

    validate_fanchart_data(data)

    fill_color_light = hex_to_rgba(color, 0.3)
    fill_color_dark = hex_to_rgba(color, 0.6)
    line_color = hex_to_rgba(color, 1)

    def get_default_trace(statistics_name: str, values: np.ndarray) -> Dict[str, Any]:
        trace = {
            "name": legend_group,
            "x": data.samples if direction == TraceDirection.HORIZONTAL else values,
            "y": values if direction == TraceDirection.HORIZONTAL else data.samples,
            "xaxis": xaxis,
            "yaxis": yaxis,
            "mode": "lines",
            "line": {"width": 0, "color": line_color, "shape": line_shape},
            "legendgroup": legend_group,
            "showlegend": False,
        }
        if hovermode is not None:
            trace["hovermode"] = hovermode
        if hovertemplate is not None:
            trace["hovertemplate"] = hovertemplate + statistics_name
        else:
            trace["hovertext"] = statistics_name + " " + hovertext
        return trace

    traces: List[Dict[str, Any]] = []

    if data.minimum is not None:
        traces.append(
            get_default_trace(
                statistics_name="Minimum",
                values=data.minimum,
            )
        )

    if data.low is not None:
        low_trace = get_default_trace(
            statistics_name=low_percentile_name,
            values=data.low,
        )
        # Add fill to previous trace
        if len(traces) > 0:
            low_trace["fill"] = "tonexty"
            low_trace["fillcolor"] = fill_color_light
        traces.append(low_trace)

    if data.high is not None:
        high_trace = get_default_trace(
            statistics_name=high_percentile_name,
            values=data.high,
        )
        # Add fill to previous trace
        if len(traces) > 0:
            high_trace["fill"] = "tonexty"
            high_trace["fillcolor"] = fill_color_dark
        traces.append(high_trace)

    if data.maximum is not None:
        maximum_trace = get_default_trace(
            statistics_name="Maximum",
            values=data.maximum,
        )
        # Add fill to previous trace (opposite color of previous fill)
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
        mean_trace = get_default_trace(
            statistics_name="Mean",
            values=data.mean,
        )
        # Set solid line for mean
        mean_trace["line"] = {"color": line_color, "shape": line_shape}
        traces.append(mean_trace)

    # Set legend for last trace in list
    if len(traces) > 0:
        traces[-1]["showlegend"] = show_legend

    return traces
