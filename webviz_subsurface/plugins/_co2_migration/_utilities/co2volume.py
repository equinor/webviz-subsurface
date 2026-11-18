# pylint: disable=too-many-lines
# pylint: disable=C0103
# NBNB-AS: We should address this pylint message soon
import re
import warnings
from datetime import datetime as dt
from itertools import product
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from webviz_subsurface._utils.enum_shim import StrEnum
from webviz_subsurface.plugins._co2_migration._utilities.containment_info import (
    ContainmentInfo,
    MainTabOption,
)
from webviz_subsurface.plugins._co2_migration._utilities.generic import (
    Co2MassScale,
    Co2VolumeScale,
)


class Marks(StrEnum):
    dissolved_water = "/"
    dissolved_oil = "x"
    gas = ""
    free_gas = ""
    trapped_gas = "."
    moving_gas = ""
    stationary_gas = "+"
    moving_free_gas = ""
    stationary_free_gas = "+"


class Lines(StrEnum):
    dissolved_water = "dash"
    dissolved_oil = "longdash"
    gas = "dot"
    free_gas = "dot"
    trapped_gas = "longdashdot"
    moving_gas = "dot"
    stationary_gas = "dashdot"
    moving_free_gas = "dot"
    stationary_free_gas = "dashdot"


_CONTAINMENT_COLORS = {
    "total": ("#222222", "#909090"),
    "contained": ("#00aa00", "#55ff55"),
    "outside": ("#006ddd", "#6eb6ff"),
    "nogo": ("#dd4300", "#ff9a6e"),
}


_PHASE_COLORS = {
    "total": ("#222222", "#909090"),
    "dissolved_water": ("#208eb7", "#81cde9"),
    "dissolved_oil": ("#A0522D", "#C28163"),
    "gas": ("#C41E3A", "#E42E5A"),
    "free_gas": ("#C41E3A", "#E42E5A"),
    "trapped_gas": ("#2E8B57", "#66CDAA"),
    "moving_gas": ("#C41E3A", "#E42E5A"),
    "stationary_gas": ("#FF6B00", "#FF9F40"),
    "moving_free_gas": ("#C41E3A", "#E42E5A"),
    "stationary_free_gas": ("#FF6B00", "#FF9F40"),
}


_GENERAL_COLORS = [
    ("#e91451", "#f589a8"),
    ("#daa218", "#f2d386"),
    ("#208eb7", "#81cde9"),
    ("#84bc04", "#cdfc63"),
    ("#b74532", "#e19e92"),
    ("#9a89b4", "#ccc4d9"),
    ("#8d30ba", "#c891e3"),
    ("#256b33", "#77d089"),
    ("#95704d", "#cfb7a1"),
    ("#1357ca", "#7ba7f3"),
    ("#f75ef0", "#fbaef7"),
    ("#34b36f", "#93e0b7"),
]


_LIGHTER_COLORS = {
    "black": "#909090",
    **dict(_CONTAINMENT_COLORS.values()),
    **dict(_PHASE_COLORS.values()),
    **dict(_GENERAL_COLORS),
}

_LABEL_TRANSLATIONS = {
    "nogo": "no-go",
    "dissolved_water": "dissolved water",
    "dissolved_oil": "dissolved oil",
    "free_gas": "free gas",
    "trapped_gas": "trapped gas",
    "moving_gas": "moving gas",
    "stationary_gas": "stationary gas",
    "moving_free_gas": "moving free gas",
    "stationary_free_gas": "stationary free gas",
}


def _translate_labels(df: Union[pd.DataFrame, Dict], column: str = "type") -> None:
    def translate_label(label: str) -> str:
        if ", " in label:
            parts = label.split(", ")
            translated_parts = [_LABEL_TRANSLATIONS.get(part, part) for part in parts]
            return ", ".join(translated_parts)
        return _LABEL_TRANSLATIONS.get(label, label)

    if isinstance(df, dict):
        df[column] = [translate_label(label) for label in df[column]]
    else:
        df[column] = df[column].apply(translate_label)


def _get_colors(color_options: List[str], split: str) -> List[str]:
    if split == "containment":
        return [_CONTAINMENT_COLORS[option][0] for option in color_options]
    if split == "phase":
        return [_PHASE_COLORS[option][0] for option in color_options]
    options = [x[0] for x in _GENERAL_COLORS]
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
    if not categories:
        return []
    if "no-go" in categories:
        default_option = "no-go"
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


def complete_missing_spatial_data(
    df: pd.DataFrame,
    containment_info: ContainmentInfo,
    active_tab: MainTabOption,
) -> pd.DataFrame:
    if df.empty:
        return df
    spatial_columns = ["zone", "region", "plume_group"]
    grouped_columns = [containment_info.color_choice, containment_info.mark_choice]
    needs_completion = any(
        column in grouped_columns
        or getattr(containment_info, column) not in (None, "all")
        for column in spatial_columns
    )
    if not needs_completion:
        return df
    if active_tab != MainTabOption.CONTAINMENT_OVER_TIME:
        df = df.loc[df["date"] == containment_info.date_option]
    if df.empty:
        return df.copy()

    base_columns = ["REAL", "date", "phase", "containment"]
    supported = df[base_columns].drop_duplicates()
    spatial_options = []
    for column in spatial_columns:
        if column in grouped_columns:
            spatial_options.append(
                [
                    value
                    for value in (getattr(containment_info, f"{column}s") or [])
                    if value != "all"
                ]
            )
        else:
            value = getattr(containment_info, column)
            spatial_options.append([value])
            df = df.loc[df[column] == value]

    spatial_grid = pd.DataFrame(product(*spatial_options), columns=spatial_columns)
    expected = (
        supported.assign(_cross_key=0)
        .merge(spatial_grid.assign(_cross_key=0), on="_cross_key")
        .drop(columns="_cross_key")
    )
    keys = base_columns + spatial_columns
    missing = expected.merge(
        df[keys].drop_duplicates(), on=keys, how="left", indicator=True
    )
    missing = missing.loc[missing["_merge"] == "left_only", keys]
    if not missing.empty:
        df = pd.concat([df, missing.assign(amount=0.0)], ignore_index=True)
    return df.sort_values(["REAL", "date"], kind="stable").reset_index(drop=True)


def _prepare_co2_at_date(
    df: pd.DataFrame,
    scale: Union[Co2MassScale, Co2VolumeScale],
    containment_info: ContainmentInfo,
) -> pd.DataFrame:
    color_choice = containment_info.color_choice
    mark_choice = containment_info.mark_choice

    date_option = containment_info.date_option
    df.query("date == @date_option", inplace=True)

    _add_sort_keys(df, containment_info)
    _filter_columns(df, color_choice, mark_choice, containment_info)
    _filter_rows(df, color_choice, mark_choice)
    _scale_df(df, scale, color_choice, mark_choice)

    df.sort_values(
        ["sort_key", "sort_key_secondary"],
        inplace=True,
        ascending=[True, True],
    )
    return df


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


def _scale_df(
    df: pd.DataFrame,
    scale: Union[Co2MassScale, Co2VolumeScale],
    color_choice: str,
    mark_choice: str,
) -> None:
    scale_factor = 1.0
    if scale == Co2MassScale.KG:
        scale_factor = 0.001
    elif scale == Co2MassScale.MTONS:
        scale_factor = 1e6
    elif scale == Co2VolumeScale.BILLION_CUBIC_METERS:
        scale_factor = 1e9
    elif scale in (Co2MassScale.NORMALIZE, Co2VolumeScale.NORMALIZE):
        groups = df["REAL"]

        targets = {"total", "all"}
        target_rows = df[color_choice].isin(targets)
        if mark_choice in df.columns:
            target_rows |= df[mark_choice].isin(targets)

        use_max = target_rows.groupby(groups, sort=False).transform("any")
        max_amount = df["amount"].groupby(groups, sort=False).transform("max")

        if "date" in df.columns:
            totals_by_date = (
                df["amount"]
                .groupby(
                    [groups, df["date"]],
                    sort=False,
                )
                .transform("sum")
            )
            summed_amount = totals_by_date.groupby(
                groups,
                sort=False,
            ).transform("max")
        else:
            summed_amount = (
                df["amount"]
                .groupby(
                    groups,
                    sort=False,
                )
                .transform("sum")
            )

        normalization_factor = max_amount.where(use_max, summed_amount)
        needs_scaling = (normalization_factor != 0) & (normalization_factor != 1.0)
        df.loc[needs_scaling, "amount"] /= normalization_factor.loc[needs_scaling]
        return
    if scale_factor != 1.0:
        df["amount"] /= scale_factor


def _add_sort_keys(
    df: pd.DataFrame,
    containment_info: ContainmentInfo,
) -> None:
    sort_scope = (
        (df["phase"] == "total")
        & (df["zone"] == containment_info.zone)
        & (df["region"] == containment_info.region)
        & (df["plume_group"] == containment_info.plume_group)
        & df["containment"].isin(["nogo", "outside"])
    )

    sort_totals = (
        df.loc[sort_scope]
        .groupby(["REAL", "containment"], sort=False)["amount"]
        .sum()
        .unstack(fill_value=0.0)
        .reindex(columns=["nogo", "outside"], fill_value=0.0)
    )

    df["sort_key"] = df["REAL"].map(sort_totals["nogo"]).fillna(0.0)
    df["sort_key_secondary"] = df["REAL"].map(sort_totals["outside"]).fillna(0.0)


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
    fig.layout.title.yref = "container"
    fig.layout.title.y = 1
    fig.layout.title.yanchor = "top"
    fig.layout.title.pad = {"t": 10}
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
    group_columns: Union[str, List[str]],
    filter_columns: Optional[List[str]] = None,
) -> None:
    if isinstance(group_columns, str):
        group_columns = [group_columns]
    if filter_columns is None:
        amounts_for_sum = df["amount"]
    else:
        valid = pd.Series(True, index=df.index)
        for filter_column in filter_columns:
            if filter_column in df.columns:
                valid &= ~df[filter_column].isin(["total", "all"])
        amounts_for_sum = df["amount"].where(valid, 0.0)

    group_sum = amounts_for_sum.groupby(
        [df[column] for column in group_columns],
        sort=False,
    ).transform("sum")

    proportion = pd.Series(0.0, index=df.index)
    nonzero = group_sum > 0
    proportion.loc[nonzero] = (
        np.round(df.loc[nonzero, "amount"] / group_sum.loc[nonzero] * 1000) / 10
    )

    df["prop"] = proportion


def _empty_containment_figure(
    scale: Union[Co2MassScale, Co2VolumeScale],
    containment_info: ContainmentInfo,
    over_time: bool = False,
) -> go.Figure:
    fig = go.Figure()
    fig.layout.xaxis.title = "Time" if over_time else scale.value
    fig.layout.yaxis.title = scale.value if over_time else "Realization"
    _adjust_figure(fig, _make_title(containment_info, include_date=not over_time))
    return fig


def generate_co2_volume_figure(
    df: pd.DataFrame,
    scale: Union[Co2MassScale, Co2VolumeScale],
    containment_info: ContainmentInfo,
    legendonly_traces: Optional[List[str]],
) -> go.Figure:
    df = _prepare_co2_at_date(df, scale, containment_info)
    if df.empty:
        return _empty_containment_figure(scale, containment_info)
    color_choice = containment_info.color_choice
    mark_choice = containment_info.mark_choice

    df["REAL"] = df["REAL"].astype(str)
    _add_prop_to_df(df, "REAL")
    cat_ord, colors, marks = _prepare_pattern_and_color_options(
        df,
        containment_info,
        color_choice,
        mark_choice,
    )
    _translate_labels(df, "type")
    _translate_labels(cat_ord, "type")

    fig = px.bar(
        df,
        y="REAL",
        x="amount",
        color="type",
        color_discrete_sequence=colors,
        pattern_shape="type" if mark_choice != "none" else None,
        pattern_shape_sequence=marks,
        orientation="h",
        category_orders=cat_ord,
        custom_data=["prop"],
    )
    fig.update_traces(
        hovertemplate=(
            "<span style='font-family:Courier New;'>"
            "Type       : %{data.name}<br>"
            "Amount     : %{x:.3f}<br>"
            "Realization: %{y}<br>"
            "Proportion : %{customdata[0]:.1f}%"
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
    df: pd.DataFrame,
    scale: Union[Co2MassScale, Co2VolumeScale],
    y_limits: List[Optional[float]],
    containment_info: ContainmentInfo,
) -> go.Figure:
    color_choice = containment_info.color_choice
    mark_choice = containment_info.mark_choice
    _filter_columns(df, color_choice, mark_choice, containment_info)
    _filter_rows(df, color_choice, mark_choice)

    y_limits = list(y_limits)
    if df.empty:
        fig = _empty_containment_figure(scale, containment_info, over_time=True)
        fig.layout.yaxis.range = y_limits
        return fig
    _scale_df(df, scale, color_choice, mark_choice)
    if containment_info.sorting == "marking" and mark_choice != "none":
        sort_order = ["date", mark_choice]
    else:
        sort_order = ["date", color_choice]
    df.sort_values(by=sort_order, inplace=True)
    if y_limits[0] is None and y_limits[1] is not None:
        y_limits[0] = 0.0
    elif y_limits[1] is None and y_limits[0] is not None:
        maximum = df.groupby("date")["amount"].sum().max()
        y_limits[1] = maximum * 1.05
        if y_limits[1] <= y_limits[0]:
            y_limits[1] = y_limits[0] + 1.0
    elif (df["amount"] == 0.0).all() and y_limits == [None, None]:
        y_limits = [0.0, 1.0]

    _add_prop_to_df(df, "date")
    cat_ord, colors, marks = _prepare_pattern_and_color_options(
        df,
        containment_info,
        color_choice,
        mark_choice,
    )
    _translate_labels(df, "type")
    _translate_labels(cat_ord, "type")

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
        custom_data=["prop"],
    )
    fig.update_traces(
        hovertemplate=(
            "<span style='font-family:Courier New;'>"
            "Type      : %{data.name}<br>"
            "Date      : %{x}<br>"
            "Amount    : %{y:.3f}<br>"
            "Proportion: %{customdata[0]:.1f}%"
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
    if len(dates) == 0:
        return {}
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
    if df.empty:
        return
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    months += ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    dates = np.unique(df["date"])
    date_strings = {
        date: f"{months[int(date.split('-')[1]) - 1]} {date.split('-')[0]}"
        for date in dates
    }
    prev_vals = {date: 0.0 for date in dates}
    date_dict = spaced_dates(dates, 4)  # type: ignore[arg-type]

    x_values = []
    y_values = []
    hover_texts = []
    hover_colors = []

    for name, color in zip(cat_ord["type"], colors):
        sub_df = df[df["type"] == name]

        for date in dates:
            date_df = sub_df[sub_df["date"] == date]
            # Skip if no data or duplicate data for this type/date combination
            if len(date_df) != 1:
                continue

            amount = date_df["amount"].item()
            prop = date_df["prop"].item()
            prev_val = prev_vals[date]

            field_x = date_dict[date] * 8
            field_y = np.linspace(
                prev_val + 0.15 * amount,
                prev_val + 0.85 * amount,
                8,
            ).tolist() * len(date_dict[date])
            field_y.sort()

            hover_text = (
                "<span style='font-family:Courier New;'>"
                f"Type      : {name}<br>"
                f"Date      : {date_strings[date]}<br>"
                f"Amount    : {amount:.3f}<br>"
                f"Proportion: {prop:.1f}%"
                "</span>"
            )

            x_values.extend(field_x)
            y_values.extend(field_y)
            hover_texts.extend([hover_text] * len(field_x))
            hover_colors.extend([color] * len(field_x))

            # Keep unrelated fields disconnected.
            x_values.append(None)
            y_values.append(None)
            hover_texts.append(None)
            hover_colors.append(color)

            prev_vals[date] = prev_val + amount

    if not x_values:
        return

    x_values.pop()
    y_values.pop()
    hover_texts.pop()
    hover_colors.pop()

    fig.add_trace(
        go.Scatter(
            x=x_values,
            y=y_values,
            text=hover_texts,
            mode="lines",
            opacity=0,
            hoverinfo="text",
            hoveron="points",
            hoverlabel={"bgcolor": hover_colors},
            showlegend=False,
        )
    )


def _connect_plume_groups(
    df: pd.DataFrame,
    color_choice: str,
    mark_choice: str,
) -> None:
    col_list = ["REAL"]
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
            # Assumes the data frame is sorted on date. shift() makes the first row
            # in each group ineligible, independently of its index label.
            mask_end = (df_sub2["amount"] == 0.0) & (df_sub2["amount"].shift(1) > 0.0)
            mask_start = (df_sub2["amount"] > 0.0) & (df_sub2["amount"].shift(1) == 0.0)
            transition_row_end = (
                df_sub2.loc[mask_end].iloc[0] if mask_end.any() else None
            )
            transition_row_start = (
                df_sub2.loc[mask_start].iloc[0] if mask_start.any() else None
            )
            if transition_row_end is not None:
                end_points.append(transition_row_end)
                # Replace 0 with np.nan for all dates after this
                date = str(transition_row_end["date"])
                df.loc[
                    (df["plume_group"] == plume_name)
                    & df[col_list].eq(transition_row_end[col_list]).all(axis=1)
                    & (df["amount"] == 0.0)
                    & (df["date"] > date),
                    "amount",
                ] = np.nan
            if transition_row_start is not None:
                start_points.append(transition_row_start)
    for end_point in end_points:
        plume1 = end_point["plume_group"]
        match_columns = ["date", *col_list]
        row1 = end_point[match_columns]
        for start_point in start_points:
            plume2 = start_point["plume_group"]
            if plume1 in plume2 and len(plume1) < len(plume2):
                row2 = start_point[match_columns]
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


def _add_time_containment_trace(
    fig: go.Figure,
    category_df: pd.DataFrame,
    name: str,
    line_type: str,
    line_width: float,
    line_color: str,
    series_label: Union[int, str],
    hover_template: str,
    inactive_names: List[str],
    include_proportion: bool,
) -> None:
    if category_df.empty:
        return

    args = {
        "x": category_df["date"],
        "y": category_df["amount"],
        "showlegend": False,
        "line_dash": line_type,
        "line_width": line_width,
        "marker_color": line_color,
        "legendgroup": name,
        "name": "",
        "meta": [series_label, name],
        "hovertemplate": hover_template,
    }
    if include_proportion:
        args["customdata"] = category_df["prop"]
    if name in inactive_names:
        args["visible"] = "legendonly"

    fig.add_scatter(**args)


def _add_merged_realization_trace(
    fig: go.Figure,
    category_df: pd.DataFrame,
    name: str,
    color: str,
    line_type: str,
    hover_template: str,
    inactive_names: List[str],
) -> None:
    if category_df.empty:
        return

    x_values = []
    y_parts = []
    custom_data_parts = []

    for realization, realization_df in category_df.groupby("REAL", sort=False):
        amounts = realization_df["amount"].to_numpy(dtype=np.float64, copy=False)
        proportions = realization_df["prop"].to_numpy(dtype=np.float32, copy=False)

        x_values.extend(realization_df["date"].tolist())
        x_values.append(None)

        y_parts.extend((amounts, np.array([np.nan], dtype=np.float64)))
        custom_data_parts.extend(
            (
                np.column_stack(
                    (
                        np.full(amounts.size, realization, dtype=np.float32),
                        proportions,
                    )
                ),
                np.full((1, 2), np.nan, dtype=np.float32),
            )
        )

    x_values.pop()
    y_values = np.concatenate(y_parts)[:-1]
    custom_data = np.concatenate(custom_data_parts, axis=0)[:-1]

    fig.add_scatter(
        x=x_values,
        y=y_values,
        customdata=custom_data,
        showlegend=False,
        line_dash=line_type,
        line_width=2.5,
        marker_color=color,
        legendgroup=name,
        name="",
        # None tells CSV export that realization is stored per point.
        meta=[None, name],
        hovertemplate=hover_template,
        visible="legendonly" if name in inactive_names else True,
    )


# pylint: disable=too-many-locals, too-many-statements
def generate_co2_time_containment_figure(
    df: pd.DataFrame,
    scale: Union[Co2MassScale, Co2VolumeScale],
    containment_info: ContainmentInfo,
    legendonly_traces: Optional[List[str]],
) -> go.Figure:
    color_choice = containment_info.color_choice
    mark_choice = containment_info.mark_choice
    _filter_columns(df, color_choice, mark_choice, containment_info)
    _scale_df(df, scale, color_choice, mark_choice)
    options = _prepare_line_type_and_color_options(
        df, containment_info, color_choice, mark_choice
    )
    if df.empty:
        return _empty_containment_figure(scale, containment_info, over_time=True)
    _translate_labels(df, "name")
    _translate_labels(options, "name")
    if legendonly_traces is None:
        inactive_cols_at_startup = list(
            options[~(options["line_type"].isin(["solid", "0px"]))]["name"]
        )
    else:
        inactive_cols_at_startup = legendonly_traces
    fig = go.Figure()
    # Generate dummy scatters for legend entries
    date_min, date_max = df["date"].agg(["min", "max"])
    dummy_args = {
        "x": [date_min, date_max],
        "y": [None, None],
        "mode": "lines",
        "hoverinfo": "none",
    }
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
        fig.add_scatter(**dummy_args, **args)
    hover_start = (
        "<span style='font-family:Courier New;'>"
        "Type     : %{meta[1]}<br>"
        "Date     : %{x}<br>"
        "Amount   : %{y:.3f}<br>"
    )
    hover_end = "</span><extra></extra>"

    if not containment_info.show_realizations:
        df_no_real = df.drop(columns=["REAL"]).reset_index(drop=True)
        group_columns = ["date", "name", color_choice]
        if mark_choice != "none":
            group_columns.append(mark_choice)

        statistics_df = df_no_real.groupby(
            group_columns,
            as_index=False,
            sort=False,
        ).agg(
            p10=("amount", lambda values: np.quantile(values, 0.9)),
            mean=("amount", "mean"),
            p90=("amount", lambda values: np.quantile(values, 0.1)),
        )
        for statistic in ["p10", "mean", "p90"]:
            sub_df = (
                statistics_df[group_columns + [statistic]]
                .rename(columns={statistic: "amount"})
                .sort_values(["name", "date"])
                .reset_index(drop=True)
            )
            is_percentile = statistic in ["p10", "p90"]

            for name, color, line_type in zip(
                options["name"], options["color"], options["line_type"]
            ):
                _add_time_containment_trace(
                    fig=fig,
                    category_df=sub_df.loc[sub_df["name"] == name],
                    name=name,
                    line_type=line_type,
                    line_width=1.5 if is_percentile else 2.5,
                    line_color=_LIGHTER_COLORS[color] if is_percentile else color,
                    series_label=statistic,
                    hover_template=hover_start + "Statistic: %{meta[0]}" + hover_end,
                    inactive_names=inactive_cols_at_startup,
                    include_proportion=False,
                )
    else:
        hover_middle = (
            "Realization: %{customdata[0]:.0f}<br>" "Proportion : %{customdata[1]:.1f}%"
        )
        _add_prop_to_df(df, ["REAL", "date"], [color_choice, mark_choice])
        display_df = df
        if "plume_group" in df:
            display_df = df.copy()
            display_df.sort_values(["REAL", "date"], kind="stable", inplace=True)
            _connect_plume_groups(display_df, color_choice, mark_choice)

        for name, color, line_type in zip(
            options["name"], options["color"], options["line_type"]
        ):
            _add_merged_realization_trace(
                fig=fig,
                category_df=display_df.loc[display_df["name"] == name],
                name=name,
                color=color,
                line_type=line_type,
                hover_template=hover_start + hover_middle + hover_end,
                inactive_names=inactive_cols_at_startup,
            )
    # Note: The current implementation of CSV export in extract_df_from_fig()
    #       uses 'meta'/'customdata' to extract realization number and name.
    #       Make sure to keep it in sync when modifying.
    fig.layout.legend.tracegroupgap = 0
    fig.layout.xaxis.title = "Time"
    fig.layout.yaxis.title = scale.value
    fig.layout.yaxis.autorange = True
    _adjust_figure(fig, plot_title=_make_title(containment_info, include_date=False))
    return fig


def generate_co2_probability_figure(
    df: pd.DataFrame,
    scale: Union[Co2MassScale, Co2VolumeScale],
    containment_info: ContainmentInfo,
    legend_only_traces: Optional[List[str]],
) -> go.Figure:
    date_option = containment_info.date_option
    df.query("date == @date_option", inplace=True)
    df.drop(columns=["date"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    color_choice = containment_info.color_choice
    mark_choice = containment_info.mark_choice
    _filter_columns(df, color_choice, mark_choice, containment_info)
    _scale_df(df, scale, color_choice, mark_choice)
    cat_ord, colors, line_types = _prepare_pattern_and_color_options_statistics_plot(
        df,
        containment_info,
        color_choice,
        mark_choice,
    )
    if df.empty:
        fig = _empty_containment_figure(scale, containment_info)
        fig.layout.yaxis.title = "Probability"
        fig.layout.yaxis.range = [-0.02, 1.02]
        return fig
    _translate_labels(df, "type")
    _translate_labels(cat_ord, "type")

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
        hover_data=["REAL"],
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
    df: pd.DataFrame,
    scale: Union[Co2MassScale, Co2VolumeScale],
    containment_info: ContainmentInfo,
    legendonly_traces: Optional[List[str]],
) -> go.Figure:
    eps = 0.00001
    date_option = containment_info.date_option
    df.query("date == @date_option", inplace=True)
    df.drop(columns=["date"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    color_choice = containment_info.color_choice
    mark_choice = containment_info.mark_choice
    _filter_columns(df, color_choice, mark_choice, containment_info)
    _scale_df(df, scale, color_choice, mark_choice)
    cat_ord, colors, _ = _prepare_pattern_and_color_options_statistics_plot(
        df,
        containment_info,
        color_choice,
        mark_choice,
    )
    if df.empty:
        fig = _empty_containment_figure(scale, containment_info)
        fig.layout.xaxis.title = ""
        fig.layout.yaxis.title = scale.value
        return fig
    _translate_labels(df, "type")
    _translate_labels(cat_ord, "type")

    fig = go.Figure()
    for count, type_val in enumerate(cat_ord["type"], 0):
        df_sub = df[df["type"] == type_val]
        if df_sub.size == 0:
            continue

        values = df_sub["amount"].to_numpy()
        real = df_sub["REAL"].to_numpy()

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
                boxpoints=containment_info.points_to_show,
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


def _get_customdata_value(
    customdata: Any,
    row_index: int,
    column_index: int,
) -> Any:
    if isinstance(customdata, dict) and "_inputArray" in customdata:
        row = customdata["_inputArray"][row_index]
        if isinstance(row, dict):
            return row[str(column_index)]
        return row[column_index]

    return customdata[row_index][column_index]


def _extract_data_from_general_trace(
    trace: Union[go.Box, go.Scatter], plot_choice: str
) -> List[Dict[str, Any]]:
    # TODO: Find a way to avoid extracting data from metadata/hoverinfo,
    # and finding it from the trace itself.
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
        elif trace.y is not None:
            y_data = dict(enumerate(trace.y))
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
        # Merged traces use None to separate realization lines.
        if x_val is None or y_val is None:
            continue
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
                record["statistic"] = realization
            else:
                point_realization = realization
                if point_realization is None and trace.customdata is not None:
                    point_realization = int(
                        _get_customdata_value(trace.customdata, j, 0)
                    )
                record["realization"] = point_realization
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
