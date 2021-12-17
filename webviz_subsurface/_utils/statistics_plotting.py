from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class LineData:
    """
    Definition of line trace data for statistics plot

    `Attributes:`
    * `data`  - 1D np.array of value data
    * `name`  - Name of line data
    """

    data: np.ndarray
    name: str


@dataclass
class StatisticsData:
    """
    Dataclass defining statistics data utilized in creation of statistical plot traces

    `Attributes:`
    * `samples` - Common sample point list for each following value list.
    * `free_line` - LineData with name and value data for free line trace in statistics plot
     (e.g. mean, median, etc.)
    * `minimum` - Optional 1D np.array of minimum value data for statistics plot
    * `maximum` - Optional 1D np.array of maximum value data for statistics plot
    * `low` - Optional low percentile, name and 1D np.array data for statistics plot
    * `mid` - Optional middle percentile, name and 1D np.array data for statistics plot
    * `high` - Optional high percentile, name and 1D np.array data for statistics plot

    """

    # TODO:
    # - Rename mid percentile, find better name?
    # - Consider to replace all lines with List[LineData], where each free line must be
    # named and provided data.
    # - Can then be used for individual realization plots as well?
    # - One suggestion: Create base class with: samples: list, free_lines: List[LineData]
    # and inherit for "StatisticsData". Base class can be utilized for realization plots?

    samples: list = field(default_factory=list)
    free_line: Optional[LineData] = None
    minimum: Optional[np.ndarray] = None
    maximum: Optional[np.ndarray] = None
    low: Optional[LineData] = None
    high: Optional[LineData] = None
    mid: Optional[LineData] = None


def validate_statistics_data(data: StatisticsData) -> None:
    """
    Validation of statistics data

    Ensure equal length of all statistical data lists and x-axis data list

    Raise ValueError if lengths are unequal
    """
    samples_length = len(data.samples)
    if samples_length <= 0:
        raise ValueError("Empty x-axis data list in StatisticsData")
    if data.free_line is not None and samples_length != len(data.free_line.data):
        raise ValueError(
            "Invalid statistics mean value data length. len(data.samples) != len(free_line.data)"
        )
    if data.minimum is not None and samples_length != len(data.minimum):
        raise ValueError(
            "Invalid statistics minimum value data length. len(data.samples) "
            "!= len(data.minimum)"
        )
    if data.maximum is not None and samples_length != len(data.maximum):
        raise ValueError(
            "Invalid statistics maximum value data length. len(data.samples) != "
            "len(data.maximum)"
        )
    if data.low is not None and samples_length != len(data.low.data):
        raise ValueError(
            "Invalid statistics low percentile value data length. len(data.samples) "
            "!= len(data.low.data)"
        )
    if data.mid is not None and samples_length != len(data.mid.data):
        raise ValueError(
            "Invalid statistics middle percentile value data length. len(data.samples) "
            "!= len(data.mid.data)"
        )
    if data.high is not None and samples_length != len(data.high.data):
        raise ValueError(
            "Invalid statistics high percentile value data length. "
            "len(data.samples) != len(data.high.data)"
        )


# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
def create_statistics_traces(
    data: StatisticsData,
    color: str,
    legend_group: str,
    legend_name: Optional[str] = None,
    line_shape: str = "linear",
    line_width: int = 2,
    xaxis: str = "x",
    yaxis: str = "y",
    show_legend: bool = True,
    show_hoverinfo: bool = True,
    hovertext: str = "",
    hovertemplate: Optional[str] = None,
    hovermode: Optional[str] = None,
    legendrank: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Utility function for creating statistical plot traces

    Takes `data` containing data for each statistical feature as input, and creates a list of traces
    for each feature. Plotly plots traces from front to end of the list, thereby the last trace is
    plotted on top.

    Note that the data is optional, which implies that only wanted statistical features needs to be
    provided for trace plot generation.

    The function provides a list of traces: [trace0, tract1, ..., traceN]

    Note:
    If hovertemplate is proved it overrides the hovertext

    Returns:
    List of statistical line traces, one for each statistical feature in data input.
    [trace0, tract1, ..., traceN].
    """

    validate_statistics_data(data)

    def get_default_trace(statistics_name: str, values: np.ndarray) -> Dict[str, Any]:
        trace = {
            "name": legend_name if legend_name else legend_group,
            "x": data.samples,
            "y": values,
            "xaxis": xaxis,
            "yaxis": yaxis,
            "mode": "lines",
            "line": {"width": line_width, "color": color, "shape": line_shape},
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
    if data.minimum is not None:
        minimum_trace = get_default_trace(
            statistics_name="Minimum",
            values=data.minimum,
        )
        minimum_trace["line"] = {
            "color": color,
            "shape": line_shape,
            "dash": "longdash",
            "width": line_width,
        }
        traces.append(minimum_trace)

    # Low percentile
    if data.low is not None:
        low_trace = get_default_trace(
            statistics_name=data.low.name, values=data.low.data
        )
        low_trace["line"] = {
            "width": line_width,
            "color": color,
            "shape": line_shape,
            "dash": "dashdot",
        }
        traces.append(low_trace)

    # Mid percentile
    if data.mid is not None:
        mid_trace = get_default_trace(
            statistics_name=data.mid.name, values=data.mid.data
        )
        mid_trace["line"] = {
            "color": color,
            "shape": line_shape,
            "dash": "dot",
            "width": line_width,
        }
        traces.append(mid_trace)

    # High percentile
    if data.high is not None:
        high_trace = get_default_trace(
            statistics_name=data.high.name, values=data.high.data
        )
        high_trace["line"] = {
            "width": line_width,
            "color": color,
            "shape": line_shape,
            "dash": "dashdot",
        }
        traces.append(high_trace)

    # Maximum
    if data.maximum is not None:
        maximum_trace = get_default_trace(
            statistics_name="Maximum",
            values=data.maximum,
        )
        maximum_trace["line"] = {
            "color": color,
            "shape": line_shape,
            "dash": "longdash",
            "width": line_width,
        }
        traces.append(maximum_trace)

    # Free line
    if data.free_line is not None:
        line_trace = get_default_trace(
            statistics_name=data.free_line.name,
            values=data.free_line.data,
        )
        # Set solid line
        line_trace["line"] = {"width": line_width, "color": color, "shape": line_shape}
        traces.append(line_trace)

    # Set legend for last trace in list
    if len(traces) > 0:
        traces[-1]["showlegend"] = show_legend

    return traces
