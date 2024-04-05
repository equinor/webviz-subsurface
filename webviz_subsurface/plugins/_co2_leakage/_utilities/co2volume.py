import warnings
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas
import plotly.express as px
import plotly.graph_objects as go

from webviz_subsurface._providers import EnsembleTableProvider
from webviz_subsurface.plugins._co2_leakage._utilities.generic import (
    Co2MassScale,
    Co2VolumeScale,
)


class _Columns(Enum):
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
    containment_info: Dict[str, Union[str, None, List[str]]],
) -> pandas.DataFrame:
    df = table_provider.get_column_data(table_provider.column_names(), [realization])
    if any(split in list(df.columns) for split in ["zone", "region"]):
        df = _process_containment_information(df, containment_info)
    if scale_factor == 1.0:
        return df
    for col in df.columns:
        if col not in ["date", "zone", "region"]:
            df[col] /= scale_factor
    return df


def read_zone_and_region_options(
    table_provider: EnsembleTableProvider,
    realization: int,
) -> Dict[str, List[str]]:
    df = table_provider.get_column_data(table_provider.column_names(), [realization])
    zones = ["all"]
    if "zone" in list(df.columns):
        for zone in list(df["zone"]):
            if zone not in zones:
                zones.append(zone)
    regions = ["all"]
    if "region" in list(df.columns):
        for region in list(df["region"]):
            if region not in regions:
                regions.append(region)
    return {
        "zones": zones if len(zones) > 1 else [],
        "regions": regions if len(regions) > 1 else [],
    }


def _process_containment_information(
    df: pandas.DataFrame,
    containment_info: Dict[str, Union[str, None, List[str]]],
) -> pandas.DataFrame:
    choices = [containment_info["color_choice"], containment_info["mark_choice"]]
    if "zone" in choices:
        return (
            df[df["zone"] != "all"]
            .drop(columns="region", errors="ignore")
            .reset_index(drop=True)
        )
    if "region" in choices:
        return (
            df[df["region"] != "all"]
            .drop(columns="zone", errors="ignore")
            .reset_index(drop=True)
        )
    zone = containment_info["zone"]
    region = containment_info["region"]
    if zone not in ["all", None]:
        if zone in list(df["zone"]):
            return df[df["zone"] == zone].drop(
                columns=["zone", "region"], errors="ignore"
            )
        print(f"Zone {zone} not found, using sum for each unique date.")
    elif region not in ["all", None]:
        if region in list(df["region"]):
            return df[df["region"] == region].drop(
                columns=["zone", "region"], errors="ignore"
            )
        print(f"Region {region} not found, using sum for each unique date.")
    if "zone" in list(df.columns):
        if "region" in list(df.columns):
            return df[
                [a and b for a, b in zip(df["zone"] == "all", df["region"] == "all")]
            ].drop(columns=["zone", "region"])
        df = df[df["zone"] == "all"].drop(columns=["zone"])
    elif "region" in list(df.columns):
        df = df[df["region"] == "all"].drop(columns=["region"])
    return df


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
    if mark_choice == "containment":
        return ["x", "/", ""]
    if mark_choice in ["zone", "region"]:
        base_pattern = ["", "/", "x", "-", "\\", "+", "|", "."]
        if num_marks > len(base_pattern):
            base_pattern *= int(np.ceil(num_marks / len(base_pattern)))
            warnings.warn(
                f"More {type}s than pattern options. "
                f"Some {type}s will share pattern."
            )
        return base_pattern[:num_marks]
    return ["", "/"]


def _prepare_pattern_and_color_options(
    containment_info: Dict,
    color_choice: str,
    mark_choice: str,
) -> Tuple[Dict, List, List]:
    num_colors = len(containment_info[f"{color_choice}s"])
    num_marks = len(containment_info[f"{mark_choice}s"])
    marks = _get_marks(num_marks, mark_choice)
    colors = _get_colors(num_colors, color_choice)
    if containment_info["sorting"] == "color":
        cat_ord = {
            "type": [
                ", ".join((c, m))
                for c in containment_info[f"{color_choice}s"]
                for m in containment_info[f"{mark_choice}s"]
            ],
        }
        colors = [c for c in colors for _ in range(num_marks)]
        marks = marks * num_colors
    else:
        cat_ord = {
            "type": [
                ", ".join((c, m))
                for m in containment_info[f"{mark_choice}s"]
                for c in containment_info[f"{color_choice}s"]
            ],
        }
        colors = colors * num_marks
        marks = [m for m in marks for _ in range(num_colors)]
    return cat_ord, colors, marks


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
) -> pandas.DataFrame:
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
    records[mark_choice] = []
    scale_factor = _find_scale_factor(table_provider, scale)
    for real in realizations:
        df = _read_dataframe(table_provider, real, scale_factor, containment_info)
        _add_to_records(
            records, color_choice, mark_choice, df, str(real), containment_info
        )
    df = pandas.DataFrame.from_dict(records)
    df.sort_values(
        ["sort_key", "sort_key_secondary"], inplace=True, ascending=[True, True]
    )
    return df


def _add_to_records(
    records: Dict[str, List[Any]],
    color_choice: str,
    mark_choice: str,
    df: pandas.DataFrame,
    label: str,
    containment_info: Dict,
) -> None:
    assert isinstance(containment_info["containments"], List)
    assert isinstance(containment_info["phases"], List)
    phase = containment_info["phase"]
    containment = containment_info["containment"]
    split = _find_split(color_choice, mark_choice)
    if split == "standard":
        last = df.iloc[np.argmax(df["date"])]
        records["real"] += [label] * 6
        record = [
            [last["_".join((p, c))], c, p]
            for c in containment_info["containments"]
            for p in containment_info["phases"]
        ]
        records["amount"] += [r[0] for r in record]
        records["containment"] += [r[1] for r in record]
        records["phase"] += [r[2] for r in record]
        records["sort_key"] += [last["total_hazardous"]] * 6
        records["sort_key_secondary"] += [last["total_outside"]] * 6
    elif color_choice in ["zone", "region"]:
        factor = 3 if mark_choice == "containment" else 2
        last_ = df[df["date"] == np.max(df["date"])]
        records["sort_key"] += (
            [np.sum(last_["total_hazardous"])] * factor * last_.shape[0]
        )
        records["sort_key_secondary"] += (
            [np.sum(last_["total_outside"])] * factor * last_.shape[0]
        )
        for i in range(last_.shape[0]):
            last = last_.iloc[i]
            records["real"] += [label] * factor
            if mark_choice == "containment":
                assert isinstance(phase, str)
                records["amount"] += [
                    last["_".join((phase, c))] for c in containment_info["containments"]
                ]
                records[mark_choice] += containment_info["containments"]
            else:  # mark_choice == "phase"
                assert isinstance(containment, str)
                if containment == "total":
                    records["amount"] += [
                        last["total_aqueous"],
                        last["total_gas"],
                    ]
                else:
                    records["amount"] += [
                        last["_".join(("aqueous", containment))],
                        last["_".join(("gas", containment))],
                    ]
                records[mark_choice] += ["aqueous", "gas"]
            records[color_choice] += [last[split]] * factor
    else:  # color_choice == "containment", mark_choice in ["zone", "region"]:
        assert isinstance(phase, str)
        last_ = df[df["date"] == np.max(df["date"])]
        records["sort_key"] += [np.sum(last_["total_hazardous"])] * 3 * last_.shape[0]
        records["sort_key_secondary"] += (
            [np.sum(last_["total_outside"])] * 3 * last_.shape[0]
        )
        for i in range(last_.shape[0]):
            last = last_.iloc[i]
            records["real"] += [label] * 3
            records["amount"] += [
                last["_".join((phase, "contained"))],
                last["_".join((phase, "outside"))],
                last["_".join((phase, "hazardous"))],
            ]
            records[color_choice] += ["contained", "outside", "hazardous"]
            records[mark_choice] += [last[split]] * 3


def _find_split(color_choice: str, mark_choice: str) -> str:
    split = "standard"
    if "zone" in [color_choice, mark_choice]:
        split = "zone"
    elif "region" in [color_choice, mark_choice]:
        split = "region"
    return split


def _read_co2_volumes(
    table_provider: EnsembleTableProvider,
    realizations: List[int],
    scale: Union[Co2MassScale, Co2VolumeScale],
    containment_info: Dict[str, Union[str, None, List[str]]],
) -> pandas.DataFrame:
    scale_factor = _find_scale_factor(table_provider, scale)
    return pandas.concat(
        [
            _read_dataframe(
                table_provider, real, scale_factor, containment_info
            ).assign(realization=real)
            for real in realizations
        ]
    )


def _change_type_names(df: pandas.DataFrame) -> None:
    df["type"] = df["type"].replace("gas_contained", "contained, gas")
    df["type"] = df["type"].replace("gas_outside", "outside, gas")
    df["type"] = df["type"].replace("gas_hazardous", "hazardous, gas")
    df["type"] = df["type"].replace("aqueous_contained", "contained, aqueous")
    df["type"] = df["type"].replace("aqueous_outside", "outside, aqueous")
    df["type"] = df["type"].replace("aqueous_hazardous", "hazardous, aqueous")


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
    df: pandas.DataFrame,
    list_to_iterate: Union[List, np.ndarray],
    column: str,
) -> None:
    prop = np.zeros(df.shape[0])
    for element in list_to_iterate:
        summed_amount = np.sum(df.loc[df[column] == element]["amount"])
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
    cat_ord, colors, marks = _prepare_pattern_and_color_options(
        containment_info,
        color_choice,
        mark_choice,
    )
    df["type"] = [", ".join((c, p)) for c, p in zip(df[color_choice], df[mark_choice])]
    _add_prop_to_df(df, [str(r) for r in realizations], "real")
    fig = px.bar(
        df,
        y="real",
        x="amount",
        color="type",
        pattern_shape="type",
        pattern_shape_sequence=marks,
        orientation="h",
        category_orders=cat_ord,
        color_discrete_sequence=colors,
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
    df = _read_co2_volumes(
        table_provider, [time_series_realization], scale, containment_info
    )
    df.sort_values(by="date", inplace=True)
    df = df.drop(
        columns=[
            "realization",
            "REAL",
            "total",
        ]
    )
    color_choice = containment_info["color_choice"]
    mark_choice = containment_info["mark_choice"]
    split = _find_split(color_choice, mark_choice)
    if split == "standard":
        df = df.drop(
            columns=[
                "_".join(("total", c))
                for c in containment_info["containments"] + containment_info["phases"]
            ]
        )
        df = pandas.melt(df, id_vars=["date"])
    else:
        containments = containment_info["containments"]
        phases = containment_info["phases"]
        all_options = [col for col in df.columns if col not in ["date", split]]
        if mark_choice == "phase":
            if containment_info["containment"] == "total":
                cols_to_keep = ["total_gas", "total_aqueous"]
                renaming = {"total_gas": "gas", "total_aqueous": "aqueous"}
            else:
                cols_to_keep = [
                    "_".join((p, containment_info["containment"])) for p in phases
                ]
                renaming = {col: col.split("_")[0] for col in cols_to_keep}
        else:
            cols_to_keep = [
                "_".join((containment_info["phase"], c)) for c in containments
            ]
            renaming = {col: col.split("_")[1] for col in cols_to_keep}
        df = df.drop(columns=[col for col in all_options if col not in cols_to_keep])
        df = df.rename(columns=renaming)
        df = pandas.melt(df, id_vars=["date", split])
        if mark_choice == split:
            df["variable"] = df["variable"] + ", " + df[split]
        else:
            df["variable"] = df[split] + ", " + df["variable"]
        df = df.drop(columns=[split])
    cat_ord, colors, marks = _prepare_pattern_and_color_options(
        containment_info,
        color_choice,
        mark_choice,
    )
    df = df.rename(columns={"value": "amount", "variable": "type"})
    _change_type_names(df)
    if y_limits[0] is None and y_limits[1] is not None:
        y_limits[0] = 0.0
    elif y_limits[1] is None and y_limits[0] is not None:
        y_limits[1] = max(df.groupby("date")["amount"].sum()) * 1.05

    _add_prop_to_df(df, np.unique(df["date"]), "date")
    fig = px.area(
        df,
        x="date",
        y="amount",
        color="type",
        category_orders=cat_ord,
        color_discrete_sequence=colors,
        pattern_shape="type",
        pattern_shape_sequence=marks,  # ['', '/', '\\', 'x', '-', '|', '+', '.'],
        range_y=y_limits,
        hover_data=["prop"],
    )
    fig.layout.yaxis.range = y_limits
    fig.layout.xaxis.title = "Time"
    fig.layout.yaxis.title = scale.value
    _adjust_figure(fig)
    return fig


def _prepare_time_figure_options(
    df: pandas.DataFrame,
    containment_info: Dict[str, Any],
) -> Tuple[pandas.DataFrame, Dict[str, Tuple[str, str, str]], List[str]]:
    color_choice = containment_info["color_choice"]
    mark_choice = containment_info["mark_choice"]
    split = _find_split(color_choice, mark_choice)
    if split == "standard":
        df.sort_values(by="date", inplace=True)
        cols_to_plot = {
            "Total": ("total", "solid", _COLOR_TOTAL),
            "Contained": ("total_contained", "solid", _COLOR_CONTAINED),
            "Outside": ("total_outside", "solid", _COLOR_OUTSIDE),
            "Hazardous": ("total_hazardous", "solid", _COLOR_HAZARDOUS),
            "Gas": ("total_gas", "dot", _COLOR_TOTAL),
            "Aqueous": ("total_aqueous", "dash", _COLOR_TOTAL),
            "Contained mobile gas": ("gas_contained", "dot", _COLOR_CONTAINED),
            "Outside mobile gas": ("gas_outside", "dot", _COLOR_OUTSIDE),
            "Hazardous mobile gas": ("gas_hazardous", "dot", _COLOR_HAZARDOUS),
            "Contained aqueous": ("aqueous_contained", "dash", _COLOR_CONTAINED),
            "Outside aqueous": ("aqueous_outside", "dash", _COLOR_OUTSIDE),
            "Hazardous aqueous": ("aqueous_hazardous", "dash", _COLOR_HAZARDOUS),
        }
        active_cols_at_startup = ["Total", "Outside", "Hazardous", "Contained"]
    else:
        if mark_choice == "phase":
            containment = containment_info["containment"]
            phases = containment_info["phases"]
            colnames = (
                ["total", "total_gas", "total_aqueous"]
                if containment == "total"
                else ["_".join((p, containment)) for p in ["total"] + phases]
            )
            options = containment_info[f"{split}s"]
            cols_to_keep = ["date", split, "realization"] + colnames
            df = df.drop(
                columns=[col for col in df.columns if col not in cols_to_keep],
                errors="ignore",
            )
            df.sort_values(by=["date", "realization"], inplace=True)
            df_ = df[["date", "realization"]][df[split] == options[0]].reset_index(
                drop=True
            )
            for name in options:
                part_df = df[colnames][df[split] == name]
                if containment == "total":
                    part_df = part_df.rename(
                        columns={
                            c: ", ".join((name, p))
                            for c, p in zip(colnames, ["total"] + phases)
                        }
                    ).reset_index(drop=True)
                else:
                    part_df = part_df.rename(
                        columns={
                            c: ", ".join((name, c.split("_", maxsplit=1)[0]))
                            for c in colnames
                        }
                    ).reset_index(drop=True)
                df_ = pandas.concat([df_, part_df], axis=1)
            colors = _get_colors(len(options), split)
            cols_to_plot = {
                ", ".join((name, p)): (", ".join((name, p)), line_type, col)
                for p, line_type in zip(["total"] + phases, ["solid", "dot", "dash"])
                for name, col in zip(options, colors)
            }
            df_["total"] = df_[[", ".join((name, "total")) for name in options]].sum(
                axis=1
            )
            active_cols_at_startup = [name + ", total" for name in options]
        else:
            colnames = [
                "_".join((containment_info["phase"], con))
                for con in ["contained", "outside", "hazardous"]
            ]
            options = containment_info[f"{split}s"]
            df = df.drop(
                columns=[
                    "REAL",
                    "total_gas",
                    "total_aqueous",
                    "region" if split == "zone" else "zone",
                ],
                errors="ignore",
            )
            df.sort_values(by=["date", "realization"], inplace=True)
            df_ = df[["date", "realization"]][df[split] == options[0]].reset_index(
                drop=True
            )
            for name in options:
                part_df = df[colnames][df[split] == name]
                part_df = part_df.rename(
                    columns={cn: ", ".join((name, cn.split("_")[1])) for cn in colnames}
                ).reset_index(drop=True)
                df_ = pandas.concat([df_, part_df], axis=1)
            if mark_choice == split:
                colors = _get_colors(split=color_choice)
                line_types = [
                    f"{round(i / len(options) * 25)}px" for i in range(len(options))
                ]
                if len(options) > 8:
                    warnings.warn(
                        f"Large number of {split}s might make it hard "
                        f"to distinguish different dashed lines."
                    )
                cols_to_plot = {
                    ", ".join((name, con)): (", ".join((name, con)), line_type, col)
                    for con, col in zip(containment_info["containments"], colors)
                    for name, line_type in zip(options, line_types)
                }
            else:  # mark_choice == "containment"
                colors = _get_colors(len(options), split)
                cols_to_plot = {
                    ", ".join((name, con)): (", ".join((name, con)), line_type, col)
                    for con, line_type in zip(
                        ["contained", "outside", "hazardous"], ["solid", "dot", "dash"]
                    )
                    for name, col in zip(options, colors)
                }
            df_["total"] = df_[cols_to_plot.keys()].sum(axis=1)
            active_cols_at_startup = [name + ", contained" for name in options]
        df = df_
    return df, cols_to_plot, active_cols_at_startup


# pylint: disable=too-many-locals
def generate_co2_time_containment_figure(
    table_provider: EnsembleTableProvider,
    realizations: List[int],
    scale: Union[Co2MassScale, Co2VolumeScale],
    containment_info: Dict[str, Any],
) -> go.Figure:
    df = _read_co2_volumes(table_provider, realizations, scale, containment_info)
    df, cols_to_plot, active_cols_at_startup = _prepare_time_figure_options(
        df, containment_info
    )
    fig = go.Figure()
    # Generate dummy scatters for legend entries
    dummy_args = {"x": df["date"], "mode": "lines", "hoverinfo": "none"}
    for col, value in cols_to_plot.items():
        args = {
            "line_dash": value[1],
            "marker_color": value[2],
            "legendgroup": col,
            "name": col,
        }
        if col not in active_cols_at_startup:
            args["visible"] = "legendonly"
        fig.add_scatter(y=[0.0], **dummy_args, **args)
    for rlz in realizations:
        sub_df = df[df["realization"] == rlz]
        common_args = {
            "x": sub_df["date"],
            "hovertemplate": "%{x}: %{y}<br>Realization: %{meta[0]}<br>Prop: %{customdata}%",
            "meta": [rlz],
            "showlegend": False,
        }
        for col, value in cols_to_plot.items():
            prop = np.zeros(sub_df.shape[0])
            nonzero = np.where(np.array(sub_df["total"]) > 0)[0]
            prop[nonzero] = (
                np.round(
                    np.array(sub_df[value[0]])[nonzero]
                    / np.array(sub_df["total"])[nonzero]
                    * 1000
                )
                / 10
            )
            args = {
                "line_dash": value[1],
                "marker_color": value[2],
                "legendgroup": col,
                "name": col,
                "customdata": prop,
            }
            if col not in active_cols_at_startup:
                args["visible"] = "legendonly"
            fig.add_scatter(y=sub_df[value[0]], **args, **common_args)
    fig.layout.legend.tracegroupgap = 0
    fig.layout.xaxis.title = "Time"
    fig.layout.yaxis.title = scale.value
    fig.layout.yaxis.autorange = True
    _adjust_figure(fig)
    return fig
