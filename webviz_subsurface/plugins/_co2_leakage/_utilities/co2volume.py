import warnings
from datetime import datetime as dt
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from webviz_subsurface._providers import EnsembleTableProvider
from webviz_subsurface._utils.enum_shim import StrEnum
from webviz_subsurface.plugins._co2_leakage._utilities.generic import (
    Co2MassScale,
    Co2VolumeScale,
)


class _Columns(StrEnum):
    REALIZATION = "realization"
    VOLUME = "volume"
    CONTAINMENT = "containment"
    VOLUME_OUTSIDE = "volume_outside"


_COLOR_TOTAL = "#222222"
_COLOR_CONTAINED = "#00aa00"
_COLOR_OUTSIDE = "#006ddd"
_COLOR_HAZARDOUS = "#dd4300"
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


def read_menu_options(
    table_provider: EnsembleTableProvider,
    realization: int,
    relpath: str,
) -> Dict[str, List[str]]:
    col_names = table_provider.column_names()
    df = table_provider.get_column_data(col_names, [realization])
    required_columns = ["date", "amount", "phase", "containment", "zone", "region"]
    missing_columns = [col for col in required_columns if col not in col_names]
    if len(missing_columns) > 0:
        raise KeyError(
            f"Missing expected columns {', '.join(missing_columns)} in {relpath}"
            f" in realization {realization} (and possibly other csv-files). "
            f"Provided files are likely from an old version of ccs-scripts."
        )
    zones = ["all"]
    for zone in list(df["zone"]):
        if zone not in zones:
            zones.append(zone)
    regions = ["all"]
    for region in list(df["region"]):
        if region not in regions:
            regions.append(region)
    if "free_gas" in list(df["phase"]):
        phases = ["total", "free_gas", "trapped_gas", "aqueous"]
    else:
        phases = ["total", "gas", "aqueous"]
    return {
        "zones": zones if len(zones) > 1 else [],
        "regions": regions if len(regions) > 1 else [],
        "phases": phases,
    }


def _get_colors(num_cols: int = 3, split: str = "zone") -> List[str]:
    if split == "containment":
        return [_COLOR_HAZARDOUS, _COLOR_OUTSIDE, _COLOR_CONTAINED]
    options = list(_COLOR_ZONES)
    if split == "region":
        options.reverse()
    if len(options) >= num_cols:
        return options[:num_cols]
    num_lengths = int(np.ceil(num_cols / len(options)))
    new_cols = options * num_lengths
    return new_cols[:num_cols]


def _get_marks(num_marks: int, mark_choice: str) -> List[str]:
    if mark_choice == "none":
        return [""] * num_marks
    if mark_choice == "containment":
        return ["x", "/", ""]
    if mark_choice in ["zone", "region"]:
        base_pattern = ["", "/", "x", "-", "\\", "+", "|", "."]
        if num_marks > len(base_pattern):
            base_pattern *= int(np.ceil(num_marks / len(base_pattern)))
            warnings.warn(
                f"More {mark_choice}s than pattern options. "
                f"Some {mark_choice}s will share pattern."
            )
        return base_pattern[:num_marks]
    return ["", "/"] if num_marks == 2 else ["", ".", "/"]


def _get_line_types(mark_options: List[str], mark_choice: str) -> List[str]:
    if mark_choice == "none":
        return ["solid"]
    if mark_choice == "containment":
        return ["dash", "dot", "solid"]
    if mark_choice in ["zone", "region"]:
        if len(mark_options) > 8:
            warnings.warn(
                f"Large number of {mark_choice}s might make it hard "
                f"to distinguish different dashed lines."
            )
        return [
            f"{round(i / len(mark_options) * 25)}px" for i in range(len(mark_options))
        ]
    return ["dot", "dash"] if "gas" in mark_options else ["dot", "dashdot", "dash"]


def _prepare_pattern_and_color_options(
    df: pd.DataFrame,
    containment_info: Dict,
    color_choice: str,
    mark_choice: str,
) -> Tuple[Dict, List, List]:
    mark_options = [] if mark_choice == "none" else containment_info[f"{mark_choice}s"]
    color_options = containment_info[f"{color_choice}s"]
    num_colors = len(color_options)
    num_marks = num_colors if mark_choice == "none" else len(mark_options)
    marks = _get_marks(num_marks, mark_choice)
    colors = _get_colors(num_colors, color_choice)
    if mark_choice == "none":
        cat_ord = {"type": color_options}
        df["type"] = df[color_choice]
        return cat_ord, colors, marks
    df["type"] = [", ".join((c, m)) for c, m in zip(df[color_choice], df[mark_choice])]
    if containment_info["sorting"] == "color":
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


def _prepare_line_type_and_color_options(
    df: pd.DataFrame,
    containment_info: Dict,
    color_choice: str,
    mark_choice: str,
) -> pd.DataFrame:
    mark_options = []
    if mark_choice != "none":
        mark_options = list(containment_info[f"{mark_choice}s"])
    color_options = list(containment_info[f"{color_choice}s"])
    num_colors = len(color_options)
    line_types = _get_line_types(mark_options, mark_choice)
    colors = _get_colors(num_colors, color_choice)
    filter_mark = True
    if mark_choice == "phase":
        mark_options = ["total"] + mark_options
        line_types = ["solid"] + line_types
        filter_mark = False
    if color_choice == "containment":
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
    if containment_info["sorting"] == "color":
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


def _find_scale_factor(
    table_provider: EnsembleTableProvider,
    scale: Union[Co2MassScale, Co2VolumeScale],
) -> float:
    if scale in (Co2MassScale.KG, Co2VolumeScale.CUBIC_METERS):
        return 1.0
    if scale in (Co2MassScale.MTONS, Co2VolumeScale.BILLION_CUBIC_METERS):
        return 1e9
    if scale in (Co2MassScale.NORMALIZE, Co2VolumeScale.NORMALIZE):
        df = table_provider.get_column_data(table_provider.column_names())
        return df["total"].max()
    return 1.0


def _read_terminal_co2_volumes(
    table_provider: EnsembleTableProvider,
    realizations: List[int],
    scale: Union[Co2MassScale, Co2VolumeScale],
    containment_info: Dict[str, Union[str, None, List[str]]],
) -> pd.DataFrame:
    records: Dict[str, List[Any]] = {
        "real": [],
        "amount": [],
        "sort_key": [],
        "sort_key_secondary": [],
    }
    color_choice = containment_info["color_choice"]
    mark_choice = containment_info["mark_choice"]
    assert isinstance(color_choice, str)
    assert isinstance(mark_choice, str)
    records[color_choice] = []
    if mark_choice != "none":
        records[mark_choice] = []
    scale_factor = _find_scale_factor(table_provider, scale)
    data_frame = None
    for real in realizations:
        df = _read_dataframe(table_provider, real, scale_factor)
        df = df[df["date"] == np.max(df["date"])]
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
    containment_info: Dict,
) -> None:
    filter_columns = [
        col
        for col in ["phase", "containment", "zone", "region"]
        if col not in [mark_choice, color_choice]
    ]
    for col in filter_columns:
        df.query(f'{col} == "{containment_info[col]}"', inplace=True)
    df.drop(columns=filter_columns, inplace=True)


def _filter_rows(
    df: pd.DataFrame,
    color_choice: str,
    mark_choice: str,
    filter_mark: bool = True,
) -> None:
    df.query(f'{color_choice} not in ["total", "all"]', inplace=True)
    if mark_choice != "none" and filter_mark:
        df.query(f'{mark_choice} not in ["total", "all"]', inplace=True)


def _add_sort_key_and_real(
    df: pd.DataFrame,
    label: str,
    containment_info: Dict,
) -> None:
    sort_value = np.sum(
        df[
            (df["phase"] == "total")
            & (df["containment"] == "hazardous")
            & (df["zone"] == containment_info["zone"])
            & (df["region"] == containment_info["region"])
        ]["amount"]
    )
    sort_value_secondary = np.sum(
        df[
            (df["phase"] == "total")
            & (df["containment"] == "outside")
            & (df["zone"] == containment_info["zone"])
            & (df["region"] == containment_info["region"])
        ]["amount"]
    )
    df["real"] = [label] * df.shape[0]
    df["sort_key"] = [sort_value] * df.shape[0]
    df["sort_key_secondary"] = [sort_value_secondary] * df.shape[0]


def _read_co2_volumes(
    table_provider: EnsembleTableProvider,
    realizations: List[int],
    scale: Union[Co2MassScale, Co2VolumeScale],
) -> pd.DataFrame:
    scale_factor = _find_scale_factor(table_provider, scale)
    return pd.concat(
        [
            _read_dataframe(table_provider, r, scale_factor).assign(realization=r)
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


def _adjust_figure(fig: go.Figure) -> None:
    fig.layout.legend.orientation = "v"
    fig.layout.legend.title.text = ""
    fig.layout.legend.itemwidth = 40
    fig.layout.xaxis.exponentformat = "power"
    fig.layout.title.x = 0.5
    fig.layout.paper_bgcolor = "rgba(0,0,0,0)"
    fig.layout.margin.b = 6
    fig.layout.margin.t = 15
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
    table_provider: EnsembleTableProvider,
    realizations: List[int],
    scale: Union[Co2MassScale, Co2VolumeScale],
    containment_info: Dict[str, Any],
) -> go.Figure:
    df = _read_terminal_co2_volumes(
        table_provider, realizations, scale, containment_info
    )
    color_choice = containment_info["color_choice"]
    mark_choice = containment_info["mark_choice"]
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
        hover_data={"prop": True, "real": False},
    )
    fig.layout.yaxis.title = "Realization"
    fig.layout.xaxis.title = scale.value
    _adjust_figure(fig)
    return fig


# pylint: disable=too-many-locals
def generate_co2_time_containment_one_realization_figure(
    table_provider: EnsembleTableProvider,
    scale: Union[Co2MassScale, Co2VolumeScale],
    time_series_realization: int,
    y_limits: List[Optional[float]],
    containment_info: Dict[str, Any],
) -> go.Figure:
    df = _read_co2_volumes(table_provider, [time_series_realization], scale)
    color_choice = containment_info["color_choice"]
    mark_choice = containment_info["mark_choice"]
    _filter_columns(df, color_choice, mark_choice, containment_info)
    _filter_rows(df, color_choice, mark_choice)
    if containment_info["sorting"] == "marking" and mark_choice != "none":
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
        hover_data={
            "prop": True,
            "amount": ":.3f",
        },
    )
    _add_hover_info_in_field(fig, df, cat_ord, colors)
    fig.layout.yaxis.range = y_limits
    fig.layout.xaxis.title = "Time"
    fig.layout.yaxis.title = scale.value
    _adjust_figure(fig)
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
    date_dict = spaced_dates(dates, 4)
    for name, color in zip(cat_ord["type"], colors):
        sub_df = df[df["type"] == name]
        for date in dates:
            amount = sub_df[sub_df["date"] == date]["amount"].item()
            prop = sub_df[sub_df["date"] == date]["prop"].item()
            prev_val = prev_vals[date]
            p15 = prev_val + 0.15 * amount
            p85 = prev_val + 0.85 * amount
            y_vals = np.linspace(p15, p85, 8).tolist() * len(date_dict[date])
            y_vals.sort()
            fig.add_trace(
                go.Scatter(
                    x=date_dict[date] * 8,
                    y=y_vals,
                    mode="lines",
                    line=go.scatter.Line(color=color),
                    text=f"type={name}<br>date={date_strings[date]}<br>"
                    f"amount={amount:.3f}<br>prop={prop}",
                    opacity=0,
                    hoverinfo="text",
                    hoveron="points",
                    showlegend=False,
                )
            )
            prev_vals[date] = prev_val + amount


# pylint: disable=too-many-locals
def generate_co2_time_containment_figure(
    table_provider: EnsembleTableProvider,
    realizations: List[int],
    scale: Union[Co2MassScale, Co2VolumeScale],
    containment_info: Dict[str, Any],
) -> go.Figure:
    df = _read_co2_volumes(table_provider, realizations, scale)
    color_choice = containment_info["color_choice"]
    mark_choice = containment_info["mark_choice"]
    _filter_columns(df, color_choice, mark_choice, containment_info)
    options = _prepare_line_type_and_color_options(
        df, containment_info, color_choice, mark_choice
    )
    active_cols_at_startup = list(
        options[options["line_type"].isin(["solid", "0px"])]["name"]
    )
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
        if name not in active_cols_at_startup:
            args["visible"] = "legendonly"
        fig.add_scatter(y=[0.0], **dummy_args, **args)
    for rlz in realizations:
        sub_df = df[df["realization"] == rlz].copy().reset_index()
        _add_prop_to_df(
            sub_df, np.unique(df["date"]), "date", [color_choice, mark_choice]
        )
        common_args = {
            "x": sub_df["date"],
            "hovertemplate": "%{x}: %{y}<br>Realization: %{meta[0]}<br>Prop: %{customdata}%",
            "meta": [rlz],
            "showlegend": False,
        }
        for name, color, line_type in zip(
            options["name"], options["color"], options["line_type"]
        ):
            # NBNB-AS: Check this, mypy complains:
            args = {
                "line_dash": line_type,
                "marker_color": color,
                "legendgroup": name,
                "name": name,
                "customdata": sub_df[sub_df["name"] == name]["prop"],  # type: ignore
            }
            if name not in active_cols_at_startup:
                args["visible"] = "legendonly"
            fig.add_scatter(
                y=sub_df[sub_df["name"] == name]["amount"], **args, **common_args
            )
    fig.layout.legend.tracegroupgap = 0
    fig.layout.xaxis.title = "Time"
    fig.layout.yaxis.title = scale.value
    fig.layout.yaxis.autorange = True
    _adjust_figure(fig)
    return fig
