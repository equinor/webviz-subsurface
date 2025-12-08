# pylint: disable=too-many-lines
# pylint: disable=C0103
# NBNB-AS: We should address this pylint message soon
import re
import warnings
from datetime import datetime as dt
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from webviz_subsurface._providers import EnsembleTableProvider
from webviz_subsurface._utils.enum_shim import StrEnum
from webviz_subsurface.plugins._co2_migration._utilities.containment_data_provider import (
    ContainmentDataProvider,
)
from webviz_subsurface.plugins._co2_migration._utilities.containment_info import (
    ContainmentInfo,
)
from webviz_subsurface.plugins._co2_migration._utilities.generic import (
    Co2MassScale,
    Co2VolumeScale,
)


class _Columns(StrEnum):
    REALIZATION = "realization"
    VOLUME = "volume"
    CONTAINMENT = "containment"
    VOLUME_OUTSIDE = "volume_outside"


class Colors(StrEnum):
    # pylint: disable=invalid-name
    total = "#222222"
    contained = "#00aa00"
    outside = "#006ddd"
    hazardous = "#dd4300"
    dissolved_water = "#208eb7"
    dissolved_oil = "#A0522D"
    gas = "#C41E3A"
    free_gas = "#FF2400"
    trapped_gas = "#880808"


class Marks(StrEnum):
    dissolved_water = "/"
    dissolved_oil = "x"
    gas = ""
    free_gas = ""
    trapped_gas = "."


class Lines(StrEnum):
    dissolved_water = "dash"
    dissolved_oil = "longdash"
    gas = "dot"
    free_gas = "dot"
    trapped_gas = "dashdot"


_COLOR_ZONES = [
    "#e91451",
    "#daa218",
    "#208eb7",
    "#84bc04",
    "#b74532",
    "#9a89b4",
    "#8d30ba",
    "#256b33",
    "#95704d",
    "#1357ca",
    "#f75ef0",
    "#34b36f",
]

_LIGHTER_COLORS = {
    "black": "#909090",
    "#222222": "#909090",
    "#00aa00": "#55ff55",
    "#006ddd": "#6eb6ff",
    "#dd4300": "#ff9a6e",
    "#e91451": "#f589a8",
    "#daa218": "#f2d386",
    "#208eb7": "#81cde9",
    "#84bc04": "#cdfc63",
    "#b74532": "#e19e92",
    "#9a89b4": "#ccc4d9",
    "#8d30ba": "#c891e3",
    "#256b33": "#77d089",
    "#95704d": "#cfb7a1",
    "#1357ca": "#7ba7f3",
    "#f75ef0": "#fbaef7",
    "#34b36f": "#93e0b7",
    "#C41E3A": "#E42E5A",
    "#FF2400": "#FF7430",
    "#880808": "#C84848",
}


def _read_dataframe(
    table_provider: EnsembleTableProvider,
    realization: int,
    scale_factor: float,
) -> pd.DataFrame:
    df = table_provider.get_column_data(table_provider.column_names(), [realization])
    if scale_factor == 1.0:
        return df
    df["amount"] /= scale_factor
    return df


def _get_colors(color_options: List[str], split: str) -> List[str]:
    if split in {"containment", "phase"}:
        return [Colors[option] for option in color_options]
    options = list(_COLOR_ZONES)
    if split == "region":
        options.reverse()
    num_cols = len(color_options)
    if len(options) >= num_cols:
        return options[:num_cols]
    num_lengths = int(np.ceil(num_cols / len(options)))
    new_cols = options * num_lengths
    return new_cols[:num_cols]


def _get_marks(mark_options: List[str], mark_choice: str) -> List[str]:
    num_marks = len(mark_options)
    if mark_choice == "none":
        return [""] * num_marks
    if mark_choice == "containment":
        return ["x", "/", ""]
    if mark_choice in ["zone", "region", "plume_group"]:
        base_pattern = ["", "/", "x", "-", "\\", "+", "|", "."]
        if num_marks > len(base_pattern):
            base_pattern *= int(np.ceil(num_marks / len(base_pattern)))
            warnings.warn(
                f"More {mark_choice}s than pattern options. "
                f"Some {mark_choice}s will share pattern."
            )
        return base_pattern[:num_marks]
    # mark_choice == "phase":
    return [Marks[option] for option in mark_options]


def _get_line_types(mark_options: List[str], mark_choice: str) -> List[str]:
    if mark_choice == "none":
        return ["solid"]
    if mark_choice == "containment":
        return ["dash", "dot", "solid"]
    if mark_choice in ["zone", "region", "plume_group"]:
        options = ["solid", "dash", "dot", "dashdot", "longdash", "longdashdot"]
        if len(mark_options) > 6:
            warnings.warn(
                f"Large number of {mark_choice}s might make it hard "
                f"to distinguish different dashed lines."
            )
        return [options[i % 6] for i in range(len(mark_options))]
    # mark_choice == "phase":
    return [Lines[option] for option in mark_options]


def _prepare_pattern_and_color_options(
    df: pd.DataFrame,
    containment_info: ContainmentInfo,
    color_choice: str,
    mark_choice: str,
) -> Tuple[Dict, List, List]:
    no_mark = mark_choice == "none"
    mark_options = [] if no_mark else getattr(containment_info, f"{mark_choice}s")
    color_options = getattr(containment_info, f"{color_choice}s")
    marks = _get_marks(mark_options, mark_choice)
    colors = _get_colors(color_options, color_choice)
    num_colors = len(color_options)
    num_marks = num_colors if no_mark else len(mark_options)
    if no_mark:
        cat_ord = {"type": color_options}
        df["type"] = df[color_choice]
        return cat_ord, colors, marks
    df["type"] = [", ".join((c, m)) for c, m in zip(df[color_choice], df[mark_choice])]
    if containment_info.sorting == "color":
        cat_ord = {
            "type": [", ".join((c, m)) for c in color_options for m in mark_options],
        }
        colors = [c for c in colors for _ in range(num_marks)]
        marks = marks * num_colors
    else:
        cat_ord = {
            "type": [", ".join((c, m)) for m in mark_options for c in color_options],
        }
        colors = colors * num_marks
        marks = [m for m in marks for _ in range(num_colors)]
    return cat_ord, colors, marks


def _prepare_pattern_and_color_options_statistics_plot(
    df: pd.DataFrame,
    containment_info: ContainmentInfo,
    color_choice: str,
    mark_choice: str,
) -> Tuple[Dict, List, List]:
    no_mark = mark_choice == "none"
    mark_options = [] if no_mark else getattr(containment_info, f"{mark_choice}s")
    color_options = getattr(containment_info, f"{color_choice}s")
    num_colors = len(color_options)
    num_marks = num_colors if no_mark else len(mark_options)
    line_types = _get_line_types(mark_options, mark_choice)
    colors = _get_colors(color_options, color_choice)

    if mark_choice == "phase":
        mark_options = ["total"] + mark_options
        line_types = ["solid"] + line_types
        num_marks += 1
    if color_choice in ["containment", "phase"]:
        color_options = ["total"] + color_options
        colors = ["black"] + colors
        num_colors += 1

    filter_mark = mark_choice != "phase"
    filter_color = color_choice not in ["phase", "containment"]
    _filter_rows(df, color_choice, mark_choice, filter_mark, filter_color)

    if no_mark:
        cat_ord = {"type": color_options}
        df["type"] = df[color_choice]
        return cat_ord, colors, line_types
    df["type"] = [", ".join((c, m)) for c, m in zip(df[color_choice], df[mark_choice])]

    if containment_info.sorting == "color":
        cat_ord = {
            "type": [", ".join((c, m)) for c in color_options for m in mark_options],
        }
        colors = [c for c in colors for _ in range(num_marks)]
        line_types = line_types * num_colors
    else:
        cat_ord = {
            "type": [", ".join((c, m)) for m in mark_options for c in color_options],
        }
        colors = colors * num_marks
        line_types = [m for m in line_types for _ in range(num_colors)]

    for m in mark_options + ["total", "all"]:
        df["type"] = df["type"].replace(f"total, {m}", m)
        df["type"] = df["type"].replace(f"all, {m}", m)
    for m in color_options:
        df["type"] = df["type"].replace(f"{m}, total", m)
        df["type"] = df["type"].replace(f"{m}, all", m)
    cat_ord["type"] = [
        label.replace("total, ", "") if "total, " in label else label
        for label in cat_ord["type"]
    ]
    cat_ord["type"] = [
        label.replace("all, ", "") if "all, " in label else label
        for label in cat_ord["type"]
    ]
    cat_ord["type"] = [
        label.replace(", total", "") if ", total" in label else label
        for label in cat_ord["type"]
    ]
    cat_ord["type"] = [
        label.replace(", all", "") if ", all" in label else label
        for label in cat_ord["type"]
    ]

    return cat_ord, colors, line_types


def _find_default_legendonly(df: pd.DataFrame, categories: List[str]) -> List[str]:
    if "hazardous" in categories:
        default_option = "hazardous"
    else:
        max_value = -999.9
        default_option = categories[0]
        for category in categories:
            df_filtered = df[df["type"] == category]
            if df_filtered["amount"].max() > max_value:
                max_value = df_filtered["amount"].max()
                default_option = category

    # The default list should contain all categories HIDDEN in the legend, so we need
    # to create a copy of the list with default_option excluded instead.
    return [c for c in categories if c != default_option]


def _prepare_line_type_and_color_options(
    df: pd.DataFrame,
    containment_info: ContainmentInfo,
    color_choice: str,
    mark_choice: str,
) -> pd.DataFrame:
    mark_options = []
    if mark_choice != "none":
        mark_options = list(getattr(containment_info, f"{mark_choice}s"))
    color_options = list(getattr(containment_info, f"{color_choice}s"))
    line_types = _get_line_types(mark_options, mark_choice)
    colors = _get_colors(color_options, color_choice)

    filter_mark = True
    if mark_choice in ["containment", "phase"]:
        mark_options = ["total"] + mark_options
        line_types = ["solid"] + line_types
        filter_mark = False
    if color_choice in ["containment", "phase"]:
        color_options = ["total"] + color_options
        colors = ["black"] + colors
    else:
        _filter_rows(df, color_choice, mark_choice, filter_mark)
    if mark_choice == "none":
        df["name"] = df[color_choice]
        return pd.DataFrame(
            {
                "name": color_options,
                "color": colors,
                "line_type": line_types * len(colors),
            }
        )
    df["name"] = [", ".join((c, m)) for c, m in zip(df[color_choice], df[mark_choice])]
    _change_names(df, color_options, mark_options)
    if containment_info.sorting == "color":
        options = pd.DataFrame(
            {
                "name": [
                    ", ".join((c, m)) for c in color_options for m in mark_options
                ],
                "color": [c for c in colors for _ in mark_options],
                "line_type": [l for _ in colors for l in line_types],
            }
        )
    else:
        options = pd.DataFrame(
            {
                "name": [
                    ", ".join((c, m)) for m in mark_options for c in color_options
                ],
                "color": [c for _ in mark_options for c in colors],
                "line_type": [l for l in line_types for _ in colors],
            }
        )
    _change_names(options, color_options, mark_options)
    return options


def _read_terminal_co2_volumes(
    table_provider: ContainmentDataProvider,
    realizations: List[int],
    scale: Union[Co2MassScale, Co2VolumeScale],
    containment_info: ContainmentInfo,
) -> pd.DataFrame:
    records: Dict[str, List[Any]] = {
        "real": [],
        "amount": [],
        "sort_key": [],
        "sort_key_secondary": [],
    }
    color_choice = containment_info.color_choice
    mark_choice = containment_info.mark_choice
    assert isinstance(color_choice, str)
    assert isinstance(mark_choice, str)
    records[color_choice] = []
    if mark_choice != "none":
        records[mark_choice] = []
    data_frame = None
    for real in realizations:
        df = table_provider.extract_dataframe(real, scale)
        df = df[df["date"] == containment_info.date_option]
        _add_sort_key_and_real(df, str(real), containment_info)
        _filter_columns(df, color_choice, mark_choice, containment_info)
        _filter_rows(df, color_choice, mark_choice)
        if data_frame is None:
            data_frame = df
        else:
            data_frame = pd.concat([data_frame, df])
    assert data_frame is not None
    data_frame.sort_values(
        ["sort_key", "sort_key_secondary"], inplace=True, ascending=[True, True]
    )
    return data_frame


def _filter_columns(
    df: pd.DataFrame,
    color_choice: str,
    mark_choice: str,
    containment_info: ContainmentInfo,
) -> None:
    filter_columns = [
        col
        for col in ["phase", "containment", "zone", "region", "plume_group"]
        if col not in [mark_choice, color_choice]
    ]
    for col in filter_columns:
        df.query(f'{col} == "{getattr(containment_info, col)}"', inplace=True)
    df.drop(columns=filter_columns, inplace=True)


def _filter_rows(
    df: pd.DataFrame,
    color_choice: str,
    mark_choice: str,
    filter_mark: bool = True,
    filter_color: bool = True,
) -> None:
    if filter_color:
        df.query(f'{color_choice} not in ["total", "all"]', inplace=True)
    if mark_choice != "none" and filter_mark:
        df.query(f'{mark_choice} not in ["total", "all"]', inplace=True)


def _add_sort_key_and_real(
    df: pd.DataFrame,
    label: str,
    containment_info: ContainmentInfo,
) -> None:
    sort_value = np.sum(
        df[
            (df["phase"] == "total")
            & (df["containment"] == "hazardous")
            & (df["zone"] == containment_info.zone)
            & (df["region"] == containment_info.region)
            & (df["plume_group"] == containment_info.plume_group)
        ]["amount"]
    )
    sort_value_secondary = np.sum(
        df[
            (df["phase"] == "total")
            & (df["containment"] == "outside")
            & (df["zone"] == containment_info.zone)
            & (df["region"] == containment_info.region)
            & (df["plume_group"] == containment_info.plume_group)
        ]["amount"]
    )
    df["real"] = [label] * df.shape[0]
    df["sort_key"] = [sort_value] * df.shape[0]
    df["sort_key_secondary"] = [sort_value_secondary] * df.shape[0]


def _read_co2_volumes(
    table_provider: ContainmentDataProvider,
    realizations: List[int],
    scale: Union[Co2MassScale, Co2VolumeScale],
) -> pd.DataFrame:
    return pd.concat(
        [
            table_provider.extract_dataframe(r, scale).assign(realization=r)
            for r in realizations
        ]
    )


def _change_names(
    df: pd.DataFrame,
    color_options: List[str],
    mark_options: List[str],
) -> None:
    for m in mark_options + ["total", "all"]:
        df["name"] = df["name"].replace(f"total, {m}", m)
        df["name"] = df["name"].replace(f"all, {m}", m)
    for m in color_options:
        df["name"] = df["name"].replace(f"{m}, total", m)
        df["name"] = df["name"].replace(f"{m}, all", m)


def _adjust_figure(fig: go.Figure, plot_title: str) -> None:
    fig.layout.legend.orientation = "v"
    fig.layout.legend.title.text = ""
    fig.layout.legend.itemwidth = 40
    fig.layout.xaxis.exponentformat = "power"

    fig.layout.title.text = plot_title
    fig.layout.title.font = {"size": 14}
    fig.layout.margin.t = 40
    fig.layout.title.y = 0.95
    fig.layout.title.x = 0.4

    fig.layout.paper_bgcolor = "rgba(0,0,0,0)"
    fig.layout.margin.b = 6
    fig.layout.margin.l = 10
    fig.layout.margin.r = 10
    fig.update_layout(
        legend={
            "x": 1.05,
            "xanchor": "left",
        }
    )


def _add_prop_to_df(
    df: pd.DataFrame,
    list_to_iterate: Union[List, np.ndarray],
    column: str,
    filter_columns: Optional[List[str]] = None,
) -> None:
    prop = np.zeros(df.shape[0])
    for element in list_to_iterate:
        if filter_columns is None:
            summed_amount = np.sum(df.loc[df[column] == element]["amount"])
        else:
            filter_for_sum = df[column] == element
            for col in filter_columns:
                if col in df.columns:
                    filter_for_sum &= ~df[col].isin(["total", "all"])
            summed_amount = np.sum(df.loc[filter_for_sum]["amount"])
        prop[np.where(df[column] == element)[0]] = summed_amount
    nonzero = np.where(prop > 0)[0]
    prop[nonzero] = (
        np.round(np.array(df["amount"])[nonzero] / prop[nonzero] * 1000) / 10
    )
    df["prop"] = prop
    df["prop"] = df["prop"].map(lambda p: str(p) + "%")


def generate_co2_volume_figure(
    table_provider: ContainmentDataProvider,
    realizations: List[int],
    scale: Union[Co2MassScale, Co2VolumeScale],
    containment_info: ContainmentInfo,
    legendonly_traces: Optional[List[str]],
) -> go.Figure:
    df = _read_terminal_co2_volumes(
        table_provider, realizations, scale, containment_info
    )
    color_choice = containment_info.color_choice
    mark_choice = containment_info.mark_choice
    _add_prop_to_df(df, [str(r) for r in realizations], "real")
    cat_ord, colors, marks = _prepare_pattern_and_color_options(
        df,
        containment_info,
        color_choice,
        mark_choice,
    )
    fig = px.bar(
        df,
        y="real",
        x="amount",
        color="type",
        color_discrete_sequence=colors,
        pattern_shape="type" if mark_choice != "none" else None,
        pattern_shape_sequence=marks,
        orientation="h",
        category_orders=cat_ord,
        custom_data=["type", "prop"],
    )
    fig.update_traces(
        hovertemplate=(
            "<span style='font-family:Courier New;'>"
            "Type       : %{customdata[0]}<br>"
            "Amount     : %{x:.3f}<br>"
            "Realization: %{y}<br>"
            "Proportion : %{customdata[1]}"
            "</span><extra></extra>"
        ),
    )
    if legendonly_traces is not None:
        _toggle_trace_visibility(fig.data, legendonly_traces)
    fig.layout.yaxis.title = "Realization"
    fig.layout.xaxis.title = scale.value
    _adjust_figure(fig, plot_title=_make_title(containment_info))
    return fig


# pylint: disable=too-many-locals
def generate_co2_time_containment_one_realization_figure(
    table_provider: ContainmentDataProvider,
    scale: Union[Co2MassScale, Co2VolumeScale],
    time_series_realization: int,
    y_limits: List[Optional[float]],
    containment_info: ContainmentInfo,
) -> go.Figure:
    df = _read_co2_volumes(table_provider, [time_series_realization], scale)
    color_choice = containment_info.color_choice
    mark_choice = containment_info.mark_choice
    _filter_columns(df, color_choice, mark_choice, containment_info)
    _filter_rows(df, color_choice, mark_choice)
    if containment_info.sorting == "marking" and mark_choice != "none":
        sort_order = ["date", mark_choice]
    else:
        sort_order = ["date", color_choice]
    df.sort_values(by=sort_order, inplace=True)
    if y_limits[0] is None and y_limits[1] is not None:
        y_limits[0] = 0.0
    elif y_limits[1] is None and y_limits[0] is not None:
        y_limits[1] = max(df.groupby("date")["amount"].sum()) * 1.05

    _add_prop_to_df(df, np.unique(df["date"]), "date")
    cat_ord, colors, marks = _prepare_pattern_and_color_options(
        df,
        containment_info,
        color_choice,
        mark_choice,
    )
    fig = px.area(
        df,
        x="date",
        y="amount",
        color="type",
        color_discrete_sequence=colors,
        pattern_shape="type" if mark_choice != "none" else None,
        pattern_shape_sequence=marks,
        category_orders=cat_ord,
        range_y=y_limits,
        custom_data=["type", "prop"],
    )
    fig.update_traces(
        hovertemplate=(
            "<span style='font-family:Courier New;'>"
            "Type      : %{customdata[0]}<br>"
            "Date      : %{x}<br>"
            "Amount    : %{y:.3f}<br>"
            "Proportion: %{customdata[1]}"
            "</span><extra></extra>"
        ),
    )
    _add_hover_info_in_field(fig, df, cat_ord, colors)
    fig.layout.yaxis.range = y_limits
    fig.layout.xaxis.title = "Time"
    fig.layout.yaxis.title = scale.value
    _adjust_figure(fig, plot_title=_make_title(containment_info, include_date=False))
    return fig


def spaced_dates(dates: List[str], num_between: int) -> Dict[str, List[str]]:
    dates_list = [dt.strptime(date, "%Y-%m-%d") for date in dates]
    date_dict: Dict[str, List[str]] = {date: [] for date in dates}
    for i in range(len(dates_list) - 1):
        date_dict[dates[i]].append(dates[i])
        delta = (dates_list[i + 1] - dates_list[i]) / (num_between + 1)
        for j in range(1, num_between + 1):
            new_date = dates_list[i] + delta * j
            if j <= num_between / 2:
                date_dict[dates[i]].append(new_date.strftime("%Y-%m-%d"))
            else:
                date_dict[dates[i + 1]].append(new_date.strftime("%Y-%m-%d"))
    date_dict[dates[-1]].append(dates[-1])
    return date_dict


def _add_hover_info_in_field(
    fig: go.Figure,
    df: pd.DataFrame,
    cat_ord: Dict,
    colors: List,
) -> None:
    """
    Plots additional, invisible points in the middle of each field in the third plot,
    solely to display hover information inside the fields
    (which is not possible directly with plotly.express.area)
    """
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    months += ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    dates = np.unique(df["date"])
    date_strings = {
        date: f"{months[int(date.split('-')[1]) - 1]} {date.split('-')[0]}"
        for date in dates
    }
    prev_vals = {date: 0 for date in dates}
    date_dict = spaced_dates(dates, 4)  # type: ignore[arg-type]
    for name, color in zip(cat_ord["type"], colors):
        sub_df = df[df["type"] == name]
        for date in dates:
            amount = sub_df[sub_df["date"] == date]["amount"].item()
            prop = sub_df[sub_df["date"] == date]["prop"].item()
            prev_val = prev_vals[date]
            p15 = prev_val + 0.15 * amount
            p85 = prev_val + 0.85 * amount
            y_vals = np.linspace(p15, p85, 8).tolist() * len(date_dict[date])
            y_vals.sort()  # type: ignore[attr-defined]
            fig.add_trace(
                go.Scatter(
                    x=date_dict[date] * 8,
                    y=y_vals,
                    mode="lines",
                    line=go.scatter.Line(color=color),
                    text=(
                        "<span style='font-family:Courier New;'>"
                        f"Type      : {name}<br>"
                        f"Date      : {date_strings[date]}<br>"
                        f"Amount    : {amount:.3f}<br>"
                        f"Proportion: {prop}"
                    ),
                    opacity=0,
                    hoverinfo="text",
                    hoveron="points",
                    showlegend=False,
                )
            )
            prev_vals[date] = prev_val + amount


def _connect_plume_groups(
    df: pd.DataFrame,
    color_choice: str,
    mark_choice: str,
) -> None:
    col_list = ["realization"]
    if color_choice == "plume_group" and mark_choice != "none":
        col_list.append(mark_choice)
    elif mark_choice == "plume_group":
        col_list.append(color_choice)

    cols: Union[List[str], str] = col_list
    if len(col_list) == 1:
        cols = col_list[0]
    # Find points where plumes start or end, to connect the lines
    end_points = []
    start_points = []
    for plume_name, df_sub in df.groupby("plume_group"):
        if plume_name == "undetermined":
            continue
        for _, df_sub2 in df_sub.groupby(cols):
            # Assumes the data frame is sorted on date
            mask_end = (
                (df_sub2["amount"] == 0.0)
                & (df_sub2["amount"].shift(1) > 0.0)
                & (df_sub2.index > 0)
            )
            mask_start = (
                (df_sub2["amount"] > 0.0)
                & (df_sub2["amount"].shift(1) == 0.0)
                & (df_sub2.index > 0)
            )
            first_index_end = mask_end.idxmax() if mask_end.any() else None
            first_index_start = mask_start.idxmax() if mask_start.any() else None
            transition_row_end = (
                df_sub2.loc[first_index_end] if first_index_end is not None else None
            )
            transition_row_start = (
                df_sub2.loc[first_index_start]
                if first_index_start is not None
                else None
            )
            if transition_row_end is not None:
                end_points.append(transition_row_end)
                # Replace 0 with np.nan for all dates after this
                date = str(transition_row_end["date"])
                df.loc[
                    (df["plume_group"] == plume_name)
                    & (df["amount"] == 0.0)
                    & (df["date"] > date),
                    "amount",
                ] = np.nan
            if transition_row_start is not None:
                start_points.append(transition_row_start)
    for end_point in end_points:
        plume1 = end_point["plume_group"]
        row1 = end_point.drop(["amount", "plume_group", "name"])
        for start_point in start_points:
            plume2 = start_point["plume_group"]
            if plume1 in plume2 and len(plume1) < len(plume2):
                row2 = start_point.drop(["amount", "plume_group", "name"])
                if row1.equals(row2):
                    row_to_change = df.eq(end_point).all(axis=1)
                    if sum(row_to_change) == 1:
                        df.loc[row_to_change, "amount"] = start_point["amount"]
    df["is_merged"] = ["+" in x for x in df["plume_group"].values]
    df.loc[
        (df["plume_group"] != "all") & (df["is_merged"]) & (df["amount"] == 0.0),
        "amount",
    ] = np.nan
    df.drop(columns="is_merged", inplace=True)


# pylint: disable=too-many-locals, too-many-statements
def generate_co2_time_containment_figure(
    table_provider: ContainmentDataProvider,
    realizations: List[int],
    scale: Union[Co2MassScale, Co2VolumeScale],
    containment_info: ContainmentInfo,
    legendonly_traces: Optional[List[str]],
) -> go.Figure:
    df = _read_co2_volumes(table_provider, realizations, scale)
    color_choice = containment_info.color_choice
    mark_choice = containment_info.mark_choice
    _filter_columns(df, color_choice, mark_choice, containment_info)
    options = _prepare_line_type_and_color_options(
        df, containment_info, color_choice, mark_choice
    )
    if legendonly_traces is None:
        inactive_cols_at_startup = list(
            options[~(options["line_type"].isin(["solid", "0px"]))]["name"]
        )
    else:
        inactive_cols_at_startup = legendonly_traces
    if "plume_group" in df:
        try:
            _connect_plume_groups(df, color_choice, mark_choice)
        except ValueError:
            pass

    fig = go.Figure()
    # Generate dummy scatters for legend entries
    dummy_args = {"x": df["date"], "mode": "lines", "hoverinfo": "none"}
    for name, color, line_type in zip(
        options["name"], options["color"], options["line_type"]
    ):
        args = {
            "line_dash": line_type,
            "marker_color": color,
            "legendgroup": name,
            "name": name,
        }
        if name in inactive_cols_at_startup:
            args["visible"] = "legendonly"
        fig.add_scatter(y=[0.0], **dummy_args, **args)

    hover_template = (
        "<span style='font-family:Courier New;'>"
        "Type       : %{meta[1]}<br>"
        "Date       : %{x}<br>"
        "Amount     : %{y:.3f}<br>"
        "Realization: %{meta[0]}<br>"
        "Proportion : %{customdata}"
        "</span><extra></extra>"
    )

    if containment_info.use_stats:
        df_no_real = df.drop(columns=["REAL", "realization"]).reset_index(drop=True)
        if mark_choice == "none":
            df_grouped = df_no_real.groupby(
                ["date", "name", color_choice], as_index=False
            )
        else:
            df_grouped = df_no_real.groupby(
                ["date", "name", color_choice, mark_choice], as_index=False
            )
        df_mean = df_grouped.agg("mean")
        df_mean["realization"] = ["mean"] * df_mean.shape[0]
        df_p10 = df_grouped.agg(lambda x: np.quantile(x, 0.9))
        df_p10["realization"] = ["p10"] * df_p10.shape[0]
        df_p90 = df_grouped.agg(lambda x: np.quantile(x, 0.1))
        df_p90["realization"] = ["p90"] * df_p90.shape[0]
        df = (
            pd.concat([df_mean, df_p10, df_p90])
            .sort_values(["name", "date"])
            .reset_index(drop=True)
        )
        realizations = ["p10", "mean", "p90"]  # type: ignore
        hover_template = (
            "<span style='font-family:Courier New;'>"
            "Type     : %{meta[1]}<br>"
            "Date     : %{x}<br>"
            "Amount   : %{y:.3f}<br>"
            "Statistic: %{meta[0]}"
            "</span><extra></extra>"
        )
    for rlz in realizations:
        lwd = 1.5 if rlz in ["p10", "p90"] else 2.5
        sub_df = df[df["realization"] == rlz].copy().reset_index(drop=True)
        if not containment_info.use_stats:
            _add_prop_to_df(
                sub_df, np.unique(df["date"]), "date", [color_choice, mark_choice]
            )
        common_args = {
            "x": sub_df["date"],
            "showlegend": False,
        }
        for name, color, line_type in zip(
            options["name"], options["color"], options["line_type"]
        ):
            args = {
                "line_dash": line_type,
                "line_width": lwd,
                "marker_color": (
                    _LIGHTER_COLORS[color] if rlz in ["p10", "p90"] else color
                ),
                "legendgroup": name,
                "name": "",
                "meta": [rlz, name],
                "hovertemplate": hover_template,
            }
            # Note: The current implementation of CSV export in extract_df_from_fig()
            #       uses 'meta' to extract realization number and name.
            #       Make sure to keep it in sync when modifying.
            if not containment_info.use_stats:
                args["customdata"] = sub_df[sub_df["name"] == name]["prop"]
            if name in inactive_cols_at_startup:
                args["visible"] = "legendonly"
            fig.add_scatter(
                y=sub_df[sub_df["name"] == name]["amount"], **args, **common_args
            )
    fig.layout.legend.tracegroupgap = 0
    fig.layout.xaxis.title = "Time"
    fig.layout.yaxis.title = scale.value
    fig.layout.yaxis.autorange = True
    _adjust_figure(fig, plot_title=_make_title(containment_info, include_date=False))
    return fig


def generate_co2_statistics_figure(
    table_provider: ContainmentDataProvider,
    realizations: List[int],
    scale: Union[Co2MassScale, Co2VolumeScale],
    containment_info: ContainmentInfo,
    legend_only_traces: Optional[List[str]],
) -> go.Figure:
    date_option = containment_info.date_option
    df = _read_co2_volumes(table_provider, realizations, scale)
    df = df[df["date"] == date_option]
    df = df.drop(columns=["date"]).reset_index(drop=True)
    color_choice = containment_info.color_choice
    mark_choice = containment_info.mark_choice
    _filter_columns(df, color_choice, mark_choice, containment_info)
    cat_ord, colors, line_types = _prepare_pattern_and_color_options_statistics_plot(
        df,
        containment_info,
        color_choice,
        mark_choice,
    )

    df = df.drop(columns=["REAL"]).reset_index(drop=True)
    fig = px.ecdf(
        df,
        x="amount",
        ecdfmode="reversed",
        ecdfnorm="probability",
        markers=True,
        color="type",
        color_discrete_sequence=colors,
        line_dash="type" if mark_choice != "none" else None,
        line_dash_sequence=line_types,
        category_orders=cat_ord,
        hover_data=["realization"],
    )

    if legend_only_traces is None:
        default_option = _find_default_legendonly(df, cat_ord["type"])
        _toggle_trace_visibility(fig.data, default_option)
    else:
        _toggle_trace_visibility(fig.data, legend_only_traces)

    # Note: The current implementation of CSV export in extract_df_from_fig()
    #       uses the customdata+hovertemplate to extract realization number.
    #       Make sure to keep it in sync when modifying.
    fig.update_traces(
        hovertemplate=(
            "<span style='font-family:Courier New;'>"
            "Type       : %{data.name}<br>"
            "Amount     : %{x:.3f}<br>"
            "Probability: %{y:.3f}<br>"
            "Realization: %{customdata[0]}"
            "</span><extra></extra>"
        ),
    )
    fig.layout.yaxis.range = [-0.02, 1.02]
    fig.layout.legend.tracegroupgap = 0
    fig.layout.xaxis.title = scale.value
    fig.layout.yaxis.title = "Probability"
    _adjust_figure(fig, plot_title=_make_title(containment_info))

    return fig


def generate_co2_box_plot_figure(
    table_provider: ContainmentDataProvider,
    realizations: List[int],
    scale: Union[Co2MassScale, Co2VolumeScale],
    containment_info: ContainmentInfo,
    legendonly_traces: Optional[List[str]],
) -> go.Figure:
    eps = 0.00001
    date_option = containment_info.date_option
    df = _read_co2_volumes(table_provider, realizations, scale)
    df = df[df["date"] == date_option]
    df = df.drop(columns=["date"]).reset_index(drop=True)

    color_choice = containment_info.color_choice
    mark_choice = containment_info.mark_choice
    _filter_columns(df, color_choice, mark_choice, containment_info)
    cat_ord, colors, _ = _prepare_pattern_and_color_options_statistics_plot(
        df,
        containment_info,
        color_choice,
        mark_choice,
    )

    fig = go.Figure()
    for count, type_val in enumerate(cat_ord["type"], 0):
        df_sub = df[df["type"] == type_val]
        if df_sub.size == 0:
            continue

        values = df_sub["amount"].to_numpy()
        real = df_sub["realization"].to_numpy()

        median_val = df_sub["amount"].median()
        q1 = _calculate_plotly_quantiles(values, 0.25)
        q3 = _calculate_plotly_quantiles(values, 0.75)
        p10 = np.percentile(values, 90)
        p90 = np.percentile(values, 10)
        min_fence, max_fence = _calculate_plotly_whiskers(values, q1, q3)

        fig.add_trace(
            go.Box(
                x=[count] * len(values),
                y=values,
                name=type_val,
                marker_color=colors[count],
                boxpoints="all"
                if containment_info.box_show_points == "all_points"
                else "outliers",
                customdata=real,
                hovertemplate="<span style='font-family:Courier New;'>"
                "Type       : %{data.name}<br>Amount     : %{y:.3f}<br>"
                "Realization: %{customdata}"
                "</span><extra></extra>",
                legendgroup=type_val,
                width=0.55,
            )
        )

        # Note: The current implementation of CSV export in extract_df_from_fig()
        #       uses the hovertemplate text string to extract the data.
        #       Changing the hovertemplate text string might break the CSV export.

        fig.add_trace(
            go.Bar(
                x=[count],
                y=[values.max() - values.min() + 2 * eps],
                base=[values.min() - eps],
                opacity=0.0,
                hoverinfo="none",
                hovertemplate=(
                    "<span style='font-family:Courier New;'>"
                    f"Type           : {type_val}<br>"
                    f"Max            : {values.max():.3f}<br>"
                    f"Top whisker    : {max_fence:.3f}<br>"
                    f"p10 (not shown): {p10:.3f}<br>"
                    f"Q3             : {q3:.3f}<br>"
                    f"Median         : {median_val:.3f}<br>"
                    f"Q1             : {q1:.3f}<br>"
                    f"p90 (not shown): {p90:.3f}<br>"
                    f"Lower whisker  : {min_fence:.3f}<br>"
                    f"Min            : {values.min():.3f}"
                    "</span><extra></extra>"
                ),
                showlegend=False,
                legendgroup=type_val,
                name=type_val,
                marker_color=colors[count],
                width=0.56,
            )
        )

    fig.update_layout(
        xaxis={
            "tickmode": "array",
            "tickvals": list(range(len(cat_ord["type"]))),
            "ticktext": cat_ord["type"],
        }
    )

    if len(cat_ord["type"]) > 20 or legendonly_traces is None:
        default_option = _find_default_legendonly(df, cat_ord["type"])
        _toggle_trace_visibility(fig.data, default_option)
    else:
        _toggle_trace_visibility(fig.data, legendonly_traces)

    fig.layout.yaxis.autorange = True
    fig.layout.legend.tracegroupgap = 0
    fig.layout.yaxis.title = scale.value
    _adjust_figure(fig, plot_title=_make_title(containment_info))

    return fig


# pylint: disable=too-many-branches
def _make_title(c_info: ContainmentInfo, include_date: bool = True) -> str:
    components = []
    if include_date:
        components.append(c_info.date_option)
    if len(c_info.phases) > 0 and "phase" not in [
        c_info.color_choice,
        c_info.mark_choice,
    ]:
        if c_info.phase is not None and c_info.phase != "total":
            components.append(c_info.phase.capitalize())
        else:
            components.append("Phase: Total")
    if len(c_info.containments) > 0 and "containment" not in [
        c_info.color_choice,
        c_info.mark_choice,
    ]:
        if c_info.containment is not None and c_info.containment != "total":
            components.append(c_info.containment.capitalize())
        else:
            components.append("All containments areas")
    if len(c_info.zones) > 0 and "zone" not in [
        c_info.color_choice,
        c_info.mark_choice,
    ]:
        if c_info.zone is not None and c_info.zone != "all":
            components.append(c_info.zone)
        else:
            components.append("All zones")
    if (
        c_info.regions is not None
        and len(c_info.regions) > 0
        and "region"
        not in [
            c_info.color_choice,
            c_info.mark_choice,
        ]
    ):
        if c_info.region is not None and c_info.region != "all":
            components.append(c_info.region)
        else:
            components.append("All regions")
    if len(c_info.plume_groups) > 0 and "plume_group" not in [
        c_info.color_choice,
        c_info.mark_choice,
    ]:
        if c_info.plume_group is not None and c_info.plume_group != "all":
            components.append(c_info.plume_group)
        else:
            components.append("All plume groups")
    return " - ".join(components)


def _calculate_plotly_quantiles(values: np.ndarray, percentile: float) -> float:
    values_sorted = values.copy()
    values_sorted.sort()
    n_val = len(values_sorted)
    a = n_val * percentile - 0.5
    if a.is_integer():
        return float(values_sorted[int(a)])
    return float(np.interp(a, list(range(0, n_val)), values_sorted))


def _calculate_plotly_whiskers(
    values: np.ndarray, q1: float, q3: float
) -> Tuple[float, float]:
    values_sorted = values.copy()
    values_sorted.sort()
    a = q1 - 1.5 * (q3 - q1)
    b = q3 + 1.5 * (q3 - q1)
    return values[values >= a].min(), values[values <= b].max()


def _toggle_trace_visibility(traces: List, legendonly_names: List[str]) -> None:
    for t in traces:
        if t.name in legendonly_names:
            t.visible = "legendonly"
        else:
            t.visible = True


def parse_hover_template(hover_template: str) -> dict:
    parsed_hover_dict = {}
    for item in hover_template.split("<br>"):
        # Remove HTML tags (like <span style='font-family:Courier New;'>)
        clean_item = re.sub(r"<[^>]*>", "", item)
        clean_item = clean_item.strip()

        if ":" in clean_item:
            key, value = clean_item.split(":", 1)
            key = key.strip()
            value = value.strip()
            parsed_hover_dict[key] = value
    return parsed_hover_dict


def _extract_data_from_box_trace(trace: go.Box) -> dict[str, Any]:
    if hasattr(trace, "hovertemplate"):
        hover_dict = parse_hover_template(trace.hovertemplate)
        trace_name = hover_dict.get("Type", "Unknown")
        trace_name = trace_name.replace(",", "_").replace(" ", "")
        return {
            "type": trace_name,
            "min": float(hover_dict.get("Min", -1)),
            "lower_whisker": float(hover_dict.get("Lower whisker", -1)),
            "p90": float(hover_dict.get("p90 (not shown)", -1)),
            "q1": float(hover_dict.get("Q1", -1)),
            "median": float(hover_dict.get("Median", -1)),
            "q3": float(hover_dict.get("Q3", -1)),
            "p10": float(hover_dict.get("p10 (not shown)", -1)),
            "top_whisker": float(hover_dict.get("Top whisker", -1)),
            "max": float(hover_dict.get("Max", -1)),
        }
    return {}


def _extract_data_from_general_trace(
    trace: Union[go.Box, go.Scatter], plot_choice: str
) -> List[Dict[str, Any]]:
    records = []
    if plot_choice == "containment_time_multiple":
        meta_data = getattr(trace, "meta", None)
        realization = (
            meta_data[0] if meta_data is not None and len(meta_data) > 0 else -1
        )
        trace_name = (
            meta_data[1] if meta_data is not None and len(meta_data) > 1 else "Unknown"
        )
    else:
        trace_name = getattr(trace, "name", "Unknown")

    if plot_choice in ["probability", "containment_state"]:
        if trace.x is not None and "_inputArray" in trace.x:
            x_data = trace.x["_inputArray"]
            x_data = {int(k): v for k, v in x_data.items() if str(k).isdigit()}
    elif plot_choice in [
        "containment_time_single",
        "containment_time_multiple",
    ]:
        if trace.x is not None:
            x_data = dict(enumerate(trace.x))
    if plot_choice in [
        "probability",
        "containment_time_single",
        "containment_time_multiple",
    ]:
        if trace.y is not None and "_inputArray" in trace.y:
            y_data = trace.y["_inputArray"]
            y_data = {int(k): v for k, v in y_data.items() if str(k).isdigit()}
    elif plot_choice == "containment_state":
        if trace.y is not None:
            y_data = {k: int(v) for k, v in enumerate(trace.y)}
    xy_data = {k: (x_data[k], y_data[k]) for k in x_data if k in y_data}

    if plot_choice == "probability":
        custom_data = []
        if (
            hasattr(trace, "customdata")
            and trace.customdata is not None
            and hasattr(trace, "hovertemplate")
            and trace.hovertemplate is not None
        ):
            match = re.search(r"(\w+)\s*:\s*%\{customdata\[0\]\}", trace.hovertemplate)
            col_name = match.group(1).lower() if match else "customdata"
            if col_name == "realization":
                if "_inputArray" in trace.customdata:
                    custom_data = [x["0"] for x in trace.customdata["_inputArray"]]

    trace_name = trace_name.replace(",", "_").replace(" ", "")
    for j, (x_val, y_val) in xy_data.items():
        if plot_choice == "probability":
            record = {
                "type": trace_name,
                "amount": x_val,
                "probability": y_val,
            }
            if custom_data:
                record["realization"] = custom_data[j]
        elif plot_choice == "containment_state":
            record = {
                "type": trace_name,
                "amount": x_val,
                "realization": y_val,
            }
        elif plot_choice == "containment_time_single":
            record = {
                "type": trace_name,
                "date": x_val,
                "amount": y_val,
            }
        elif plot_choice == "containment_time_multiple":
            record = {
                "type": trace_name,
                "date": x_val,
                "amount": y_val,
            }
            if realization in ["p10", "p90", "mean"]:
                col_name = "statistic"
            else:
                col_name = "realization"
            record[col_name] = realization
        records.append(record)
    return records


def extract_df_from_fig(fig_data: tuple, plot_choice: str) -> pd.DataFrame:
    if plot_choice == "containment_time":
        # Distinguish between single and multiple realizations selected:
        if hasattr(fig_data[0], "stackgroup") and fig_data[0].stackgroup is not None:
            plot_choice = "containment_time_single"
        else:
            plot_choice = "containment_time_multiple"

    data_records = []
    for trace in fig_data:
        if hasattr(trace, "visible") and trace.visible == "legendonly":
            continue  # Skip hidden traces
        if plot_choice == "containment_time_multiple":
            is_data_point_trace = (
                hasattr(trace, "showlegend")
                and trace.showlegend is False
                and hasattr(trace, "name")
                and trace.name == ""
            )
            if not is_data_point_trace:
                # Only keep subset of traces that we want
                continue
        elif plot_choice == "containment_time_single":
            is_line_trace = (
                hasattr(trace, "showlegend")
                and trace.showlegend is False
                and hasattr(trace, "mode")
                and trace.mode == "lines"
            )
            if is_line_trace:
                continue
        elif plot_choice == "box":
            is_invisible_trace = (
                hasattr(trace, "showlegend")
                and trace.showlegend is False
                and hasattr(trace, "opacity")
                and trace.opacity == 0
            )
            if not is_invisible_trace:
                # Keep only the invisible box traces
                # They have all the data stored in the hover box,
                # while the visible traces only got lower/upper whisker and median
                continue

        if plot_choice == "box":
            record = _extract_data_from_box_trace(trace)
            if record:
                data_records.append(record)
        else:
            if hasattr(trace, "x") and hasattr(trace, "y"):
                records = _extract_data_from_general_trace(trace, plot_choice)
                if records:
                    data_records += records

    return pd.DataFrame(data_records)
