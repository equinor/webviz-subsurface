from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np

from .colors import hex_to_rgba_str


@dataclass
class FreeLineData:
    """
    Dataclass for defining statistics data for free line trace in fanchart

    `Attributes:`
    * `name` - Name of statistics data
    * `data` - 1D np.array of statistics value data
    """

    name: str
    data: np.ndarray


@dataclass
class LowHighData:
    """
    Definition of paired low and high percentile data for fanchart

    `Attributes:`
    * `low_data`  - 1D np.array of low percentile value data
    * `low_name`  - Name of low percentile
    * `high_data` - 1D np.array of high percentile value data
    * `high_name` - Name of high percentile
    """

    low_data: np.ndarray
    low_name: str
    high_data: np.ndarray
    high_name: str


@dataclass
class MinMaxData:
    """
    Definition of paired minimum and maximum data for fanchart

    `Attributes:`
    * `minimum` - 1D np.array of minimum value data
    * `maximum` - 1D np.array of maximum value data
    """

    minimum: np.ndarray
    maximum: np.ndarray


@dataclass
class FanchartData:
    """
    Dataclass defining fanchart data utilized in creation of statistical fanchart traces

    `Attributes:`
    * `samples` - Common sample point list for each following value list.
    * `free_line` - FreeLineData with name and value data for free line trace in fanchart (e.g.
     mean, median, etc.)
    * `minimum_maximum` - Paired optional minimum and maximum data for fanchart plotting
    * `low_high` - Paired optional low and high percentile names and data for fanchart plotting

    """

    samples: list = field(default_factory=list)
    free_line: Optional[FreeLineData] = None
    minimum_maximum: Optional[MinMaxData] = None
    low_high: Optional[LowHighData] = None


class TraceDirection(Enum):
    HORIZONTAL = 1
    VERTICAL = 2


def validate_fanchart_data(data: FanchartData) -> None:
    """
    Validation of fanchart data

    Ensure equal length of all statistical fanchart data lists and x-axis data list

    Raise ValueError if lengths are unequal
    """
    samples_length = len(data.samples)
    if samples_length <= 0:
        raise ValueError("Empty x-axis data list in FanchartData")
    if data.free_line is not None and samples_length != len(data.free_line.data):
        raise ValueError(
            "Invalid fanchart mean value data length. len(data.samples) != len(free_line.data)"
        )
    if data.minimum_maximum is not None and samples_length != len(
        data.minimum_maximum.minimum
    ):
        raise ValueError(
            "Invalid fanchart minimum value data length. len(data.samples) "
            "!= len(data.minimum_maximum.minimum)"
        )
    if data.minimum_maximum is not None and samples_length != len(
        data.minimum_maximum.maximum
    ):
        raise ValueError(
            "Invalid fanchart maximum value data length. len(data.samples) != "
            "len(data.minimum_maximum.maximum)"
        )
    if data.low_high is not None and samples_length != len(data.low_high.low_data):
        raise ValueError(
            "Invalid fanchart low percentile value data length. len(data.samples) "
            "!= len(data.low_high.low_data)"
        )
    if data.low_high is not None and samples_length != len(data.low_high.high_data):
        raise ValueError(
            "Invalid fanchart high percentile value data length. "
            "len(data.samples) != len(data.low_high.high_data)"
        )


# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
def get_fanchart_traces(
    data: FanchartData,
    hex_color: str,
    legend_group: str,
    legend_name: Optional[str] = None,
    line_shape: str = "linear",
    xaxis: str = "x",
    yaxis: str = "y",
    show_legend: bool = True,
    direction: TraceDirection = TraceDirection.HORIZONTAL,
    show_hoverinfo: bool = True,
    hovertext: str = "",
    hovertemplate: Optional[str] = None,
    hovermode: Optional[str] = None,
    legendrank: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Utility function for creating statistical fanchart traces

    Takes `data` containing data for each statistical feature as input, and creates a list of traces
    for each feature. Plotly plots traces from front to end of the list, thereby the last trace is
    plotted on top.

    Note that min and max, and high and low percentile are paired optional statistics. This implies
    that if minimum is provided, maximum must be provided as well, and vice versa. The same yields
    for low and high percentile data.

    The function provides a list of traces: [trace0, tract1, ..., traceN]

    Fanchart is created by use of fill "tonexty" configuration for the traces. Fill "tonexty" is
    missleading naming, as "tonexty" in trace1 fills to y in trace0, i.e y in previous trace.

    The order of traces are minimum, low, high, maximum and free line. Thus it is required that
    values in minimum <= low, and low <= high, and high <= maximum. Fill is setting "tonexty" in
    this function is set s.t. trace fillings are not stacked making colors in fills unchanged
    when disabling trace statistics inputs (minimum and maximum or low and high).

    Free line is last trace and is plotted on top as a line - without filling to other traces.

    Note:
    If hovertemplate is proved it overrides the hovertext

    Returns:
    List of fanchart traces, one for each statistical feature in data input.
    [trace0, tract1, ..., traceN].
    """

    validate_fanchart_data(data)

    fill_color_light = hex_to_rgba_str(hex_color, 0.3)
    fill_color_dark = hex_to_rgba_str(hex_color, 0.6)
    line_color = hex_to_rgba_str(hex_color, 1)

    def get_default_trace(statistics_name: str, values: np.ndarray) -> Dict[str, Any]:
        trace = {
            "name": legend_name if legend_name else legend_group,
            "x": data.samples if direction == TraceDirection.HORIZONTAL else values,
            "y": values if direction == TraceDirection.HORIZONTAL else data.samples,
            "xaxis": xaxis,
            "yaxis": yaxis,
            "mode": "lines",
            "line": {"width": 0, "color": line_color, "shape": line_shape},
            "legendgroup": legend_group,
            "showlegend": False,
        }
        if legendrank:
            trace["legendrank"] = legendrank
        if not show_hoverinfo:
            trace["hoverinfo"] = "skip"
            return trace
        if hovertemplate is not None:
            trace["hovertemplate"] = hovertemplate + statistics_name
        else:
            trace["hovertext"] = statistics_name + " " + hovertext
        if hovermode is not None:
            trace["hovermode"] = hovermode
        return trace

    traces: List[Dict[str, Any]] = []

    # Minimum
    if data.minimum_maximum is not None:
        traces.append(
            get_default_trace(
                statistics_name="Minimum",
                values=data.minimum_maximum.minimum,
            )
        )

    # Low and high percentile
    if data.low_high is not None:
        low_trace = get_default_trace(
            statistics_name=data.low_high.low_name,
            values=data.low_high.low_data,
        )
        # Add fill to previous trace
        if len(traces) > 0:
            low_trace["fill"] = "tonexty"
            low_trace["fillcolor"] = fill_color_light
        traces.append(low_trace)

        high_trace = get_default_trace(
            statistics_name=data.low_high.high_name,
            values=data.low_high.high_data,
        )
        high_trace["fill"] = "tonexty"
        high_trace["fillcolor"] = fill_color_dark
        traces.append(high_trace)

    # Maximum
    if data.minimum_maximum is not None:
        maximum_trace = get_default_trace(
            statistics_name="Maximum",
            values=data.minimum_maximum.maximum,
        )
        # Add fill to previous trace
        if len(traces) > 0:
            maximum_trace["fill"] = "tonexty"
            maximum_trace["fillcolor"] = fill_color_light
        traces.append(maximum_trace)

    # Free line
    if data.free_line is not None:
        line_trace = get_default_trace(
            statistics_name=data.free_line.name,
            values=data.free_line.data,
        )
        # Set solid line for mean
        line_trace["line"] = {"color": line_color, "shape": line_shape}
        traces.append(line_trace)

    # Set legend for last trace in list
    if len(traces) > 0:
        traces[-1]["showlegend"] = show_legend

    return traces
