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
    return ["", "/"]


def _prepare_pattern_and_color_options(
    containment_info: Dict,
    color_choice: str,
    mark_choice: str,
) -> Tuple[Dict, List, List]:
    num_colors = len(containment_info[f"{color_choice}s"])
    num_marks = (
        num_colors
        if mark_choice == "none"
        else len(containment_info[f"{mark_choice}s"])
    )
    marks = _get_marks(num_marks, mark_choice)
    colors = _get_colors(num_colors, color_choice)
    if mark_choice == "none":
        cat_ord = {"type": containment_info[f"{color_choice}s"]}
        return cat_ord, colors, marks
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


def _drop_unused_columns(
    df: pandas.DataFrame,
    containment_info: Dict,
    keep_realization: bool = True,
    figure: int = 2,
) -> Tuple[pandas.DataFrame, List[str]]:
    color_choice = containment_info["color_choice"]
    mark_choice = containment_info["mark_choice"]
    containment = containment_info["containment"]
    containments = containment_info["containments"]
    phase = containment_info["phase"]
    phases = containment_info["phases"]
    split = _find_split(color_choice, mark_choice)

    cols_to_keep = ["date"]
    if keep_realization:
        cols_to_keep += ["realization"]
    cols_to_return = []
    if split == "standard":
        if mark_choice == "none":
            cols_to_return += ["_".join((phase, c)) for c in containments]
        else:
            cols_to_return += [
                "_".join((p, c))
                for c in containments
                for p in phases  # ["total"] + phases
            ]
            # cols_to_return += ["total"] + ["_".join(("total", p)) for p in phases]
    else:
        cols_to_keep += [split]
        if mark_choice == split:
            cols_to_return += ["_".join((phase, c)) for c in containments]
        elif mark_choice == "none":
            if containment == "total":
                cols_to_return += (
                    ["total"] if phase == "total" else ["_".join(("total", phase))]
                )
            else:
                cols_to_return += ["_".join((phase, containment))]
        elif mark_choice == "containment":
            cols_to_return += ["_".join((phase, c)) for c in containments]
        else:
            if figure == 2:
                cols_to_return += [
                    (
                        "total"
                        if containment == "total"
                        else "_".join(("total", containment))
                    )
                ]
            cols_to_return += (
                ["total_gas", "total_aqueous"]
                if containment == "total"
                else ["_".join((p, containment)) for p in phases]
            )
    cols_to_keep += cols_to_return
    df = df.drop(columns=[col for col in df.columns if col not in cols_to_keep])
    return df, cols_to_return


def _rename_columns_figure2(
    part_df: pandas.DataFrame,
    mark_choice: str,
    name: str,
    colnames: List[str],
    containment: str,
    phases: List[str],
) -> pandas.DataFrame:
    if mark_choice == "none":
        renaming = {c: name for c in colnames}
    elif mark_choice == "phase":
        if containment == "total":
            renaming = {
                c: ", ".join((name, p)) for c, p in zip(colnames, ["total"] + phases)
            }
        else:
            renaming = {
                c: ", ".join((name, c.split("_", maxsplit=1)[0])) for c in colnames
            }
    elif mark_choice in ["zone", "region"]:
        renaming = {cn: ", ".join((cn.split("_")[1], name)) for cn in colnames}
    else:  # mark_choice == "containment"
        renaming = {cn: ", ".join((name, cn.split("_")[1])) for cn in colnames}
    part_df = part_df.rename(columns=renaming).reset_index(drop=True)
    return part_df


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
    if mark_choice != "none":
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
    phase = containment_info["phase"]
    containments = containment_info["containments"]
    split = _find_split(color_choice, mark_choice)
    if split == "standard":
        last = df.iloc[np.argmax(df["date"])]
        factor = 6 if mark_choice == "phase" else 3
        records["real"] += [label] * factor
        if mark_choice == "phase":
            record = [
                [last["_".join((p, c))], c, p]
                for c in containments
                for p in (containment_info["phases"])
            ]
        else:
            record = [[last["_".join((phase, c))], c] for c in containments]
        records["amount"] += [r[0] for r in record]
        records["containment"] += [r[1] for r in record]
        if mark_choice == "phase":
            records["phase"] += [r[2] for r in record]
        records["sort_key"] += [last["total_hazardous"]] * factor
        records["sort_key_secondary"] += [last["total_outside"]] * factor
    else:
        containment = containment_info["containment"]
        factor = 1 if mark_choice == "none" else 2 if mark_choice == "phase" else 3
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
            if mark_choice in ["containment", "zone", "region"]:
                records["amount"] += [last["_".join((phase, c))] for c in containments]
                records[mark_choice] += (
                    containments
                    if mark_choice == "containment"
                    else [last[split]] * factor
                )
            elif mark_choice == "none":
                if containment == "total":
                    records["amount"] += (
                        [last["total"]]
                        if phase == "total"
                        else [last["_".join(("total", phase))]]
                    )
                else:
                    records["amount"] += [last["_".join((phase, containment))]]
            else:  # mark_choice == "phase"
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
            records[color_choice] += (
                containments
                if mark_choice in ["zone", "region"]
                else [last[split]] * factor
            )


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
    df["type"] = df["type"].replace("total_contained", "contained, total")
    df["type"] = df["type"].replace("total_outside", "outside, total")
    df["type"] = df["type"].replace("total_hazardous", "hazardous, total")


def _change_type_names_mark_choice_none(df: pandas.DataFrame) -> None:
    df["type"] = df["type"].replace("gas_contained", "contained")
    df["type"] = df["type"].replace("gas_outside", "outside")
    df["type"] = df["type"].replace("gas_hazardous", "hazardous")
    df["type"] = df["type"].replace("aqueous_contained", "contained")
    df["type"] = df["type"].replace("aqueous_outside", "outside")
    df["type"] = df["type"].replace("aqueous_hazardous", "hazardous")
    df["type"] = df["type"].replace("total_contained", "contained")
    df["type"] = df["type"].replace("total_outside", "outside")
    df["type"] = df["type"].replace("total_hazardous", "hazardous")


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
    df["type"] = (
        [", ".join((c, p)) for c, p in zip(df[color_choice], df[mark_choice])]
        if mark_choice != "none"
        else df[color_choice]
    )
    _add_prop_to_df(df, [str(r) for r in realizations], "real")
    pattern_shape = "type" if mark_choice != "none" else None
    fig = px.bar(
        df,
        y="real",
        x="amount",
        color="type",
        pattern_shape=pattern_shape,
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


def _rename_columns_figure3(
    mark_choice: str,
    containment: str,
    cols_kept: List[str],
) -> Dict[str, str]:
    if mark_choice == "phase":
        if containment == "total":
            renaming = {"total_gas": "gas", "total_aqueous": "aqueous"}
        else:
            renaming = {col: col.split("_")[0] for col in cols_kept}
    elif mark_choice == "none":
        renaming = {}
    else:  # mark_choice == "containment"
        renaming = {col: col.split("_")[1] for col in cols_kept}
    return renaming


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
    color_choice = containment_info["color_choice"]
    mark_choice = containment_info["mark_choice"]
    split = _find_split(color_choice, mark_choice)
    containment = containment_info["containment"]
    df, colnames = _drop_unused_columns(
        df, containment_info, keep_realization=False, figure=3
    )
    if split == "standard":
        df = pandas.melt(df, id_vars=["date"])
    else:
        renaming = _rename_columns_figure3(
            mark_choice,
            containment,
            colnames,
        )
        df = df.rename(columns=renaming)
        df = pandas.melt(df, id_vars=["date", split])
        if mark_choice == "none":
            df["variable"] = df[split]
        else:
            df["variable"] = (
                df["variable"] + ", " + df[split]
                if mark_choice == split
                else df[split] + ", " + df["variable"]
            )
        df = df.drop(columns=[split])
    cat_ord, colors, marks = _prepare_pattern_and_color_options(
        containment_info,
        color_choice,
        mark_choice,
    )
    df = df.rename(columns={"value": "amount", "variable": "type"})
    if mark_choice == "none":
        _change_type_names_mark_choice_none(df)
    else:
        _change_type_names(df)
    if y_limits[0] is None and y_limits[1] is not None:
        y_limits[0] = 0.0
    elif y_limits[1] is None and y_limits[0] is not None:
        y_limits[1] = max(df.groupby("date")["amount"].sum()) * 1.05

    _add_prop_to_df(df, np.unique(df["date"]), "date")
    pattern_shape = "type" if mark_choice != "none" else None
    fig = px.area(
        df,
        x="date",
        y="amount",
        color="type",
        category_orders=cat_ord,
        color_discrete_sequence=colors,
        pattern_shape=pattern_shape,
        pattern_shape_sequence=marks,  # ['', '/', '\\', 'x', '-', '|', '+', '.'],
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


def _add_hover_info_in_field(
    fig: go.Figure,
    df: pandas.DataFrame,
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
    for name, color in zip(cat_ord["type"], colors):
        sub_df = df[df["type"] == name]
        for date in dates:
            amount = sub_df[sub_df["date"] == date]["amount"].item()
            prop = sub_df[sub_df["date"] == date]["prop"].item()
            prev_val = prev_vals[date]
            new_val = prev_val + amount
            mid_val = (prev_val + new_val) / 2
            fig.add_trace(
                go.Scatter(
                    x=[date],
                    y=[mid_val],
                    mode="lines",
                    line=go.scatter.Line(color=color),
                    text=f"type={name}<br>date={date_strings[date]}<br>"
                    f"amount={amount:.3f}<br>prop={prop}",
                    hoverinfo="text",
                    hoveron="points",
                    showlegend=False,
                )
            )
            prev_vals[date] = new_val


def _make_cols_to_plot(
    split: str,
    df_: pandas.DataFrame,
    containment_info: Dict,
) -> Tuple[Dict[str, Tuple[str, str, str]], List[str]]:
    mark_choice = containment_info["mark_choice"]
    color_choice = containment_info["color_choice"]
    phase = containment_info["phase"]
    phases = containment_info["phases"]
    containments = containment_info["containments"]
    options = containment_info[f"{split}s"]
    if mark_choice in ["phase", "none"]:
        colors = _get_colors(len(options), split)
        if mark_choice == "none":
            line_type = (
                "solid" if phase == "total" else "dot" if phase == "gas" else "dash"
            )
            cols_to_plot = {
                name: (name, line_type, col) for name, col in zip(options, colors)
            }
            df_["total"] = df_[options].sum(axis=1)
            active_cols_at_startup = options
        else:
            cols_to_plot = {
                ", ".join((name, p)): (", ".join((name, p)), line_type, col)
                for name, col in zip(options, colors)
                for p, line_type in zip(["total"] + phases, ["solid", "dot", "dash"])
            }
            df_["total"] = df_[[", ".join((name, "total")) for name in options]].sum(
                axis=1
            )
            active_cols_at_startup = [name + ", total" for name in options]
    else:
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
                ", ".join((con, name)): (", ".join((con, name)), line_type, col)
                for con, col in zip(containments, colors)
                for name, line_type in zip(options, line_types)
            }
            active_cols_at_startup = ["contained, " + name for name in options]
        else:  # mark_choice == "containment"
            colors = _get_colors(len(options), split)
            cols_to_plot = {
                ", ".join((name, con)): (", ".join((name, con)), line_type, col)
                for name, col in zip(options, colors)
                for con, line_type in zip(containments, ["dash", "dot", "solid"])
            }
            active_cols_at_startup = [name + ", contained" for name in options]
        df_["total"] = df_[cols_to_plot.keys()].sum(axis=1)
    return cols_to_plot, active_cols_at_startup


def _prepare_time_figure_options(
    df: pandas.DataFrame,
    containment_info: Dict[str, Any],
) -> Tuple[pandas.DataFrame, Dict[str, Tuple[str, str, str]], List[str]]:
    color_choice = containment_info["color_choice"]
    mark_choice = containment_info["mark_choice"]
    split = _find_split(color_choice, mark_choice)
    containment = containment_info["containment"]
    containments = containment_info["containments"]
    phase = containment_info["phase"]
    phases = containment_info["phases"]
    if split == "standard":
        df.sort_values(by="date", inplace=True)
        if mark_choice == "none":
            new_names = ["total"] + containments
            colors = [_COLOR_TOTAL, _COLOR_HAZARDOUS, _COLOR_OUTSIDE, _COLOR_CONTAINED]
            line_type = (
                "solid" if phase == "total" else "dot" if phase == "gas" else "dash"
            )
            colnames = ["total"]
            colnames += ["_".join((phase, c)) for c in containments]
            cols_to_plot = {
                new_name: (colname, line_type, color)
                for new_name, colname, color in zip(new_names, colnames, colors)
            }
            cols_to_keep = colnames + ["date", "realization"]
            cols_to_keep[0] = (
                "total" if phase == "total" else "_".join(("total", phase))
            )
            df = df.drop(columns=[col for col in df.columns if col not in cols_to_keep])
            df = df.rename(columns={cols_to_keep[0]: "total"}).reset_index(drop=True)
        else:
            cols_to_plot = {
                "total": ("total", "solid", _COLOR_TOTAL),
                "hazardous": ("total_hazardous", "solid", _COLOR_HAZARDOUS),
                "outside": ("total_outside", "solid", _COLOR_OUTSIDE),
                "contained": ("total_contained", "solid", _COLOR_CONTAINED),
                "gas": ("total_gas", "dot", _COLOR_TOTAL),
                "aqueous": ("total_aqueous", "dash", _COLOR_TOTAL),
                "hazardous, gas": ("gas_hazardous", "dot", _COLOR_HAZARDOUS),
                "outside, gas": ("gas_outside", "dot", _COLOR_OUTSIDE),
                "contained, gas": ("gas_contained", "dot", _COLOR_CONTAINED),
                "hazardous, aqueous": ("aqueous_hazardous", "dash", _COLOR_HAZARDOUS),
                "contained, aqueous": ("aqueous_contained", "dash", _COLOR_CONTAINED),
                "outside, aqueous": ("aqueous_outside", "dash", _COLOR_OUTSIDE),
            }
        active_cols_at_startup = ["total"] + containments
    else:
        options = containment_info[f"{split}s"]
        df, colnames = _drop_unused_columns(df, containment_info)
        df.sort_values(by=["date", "realization"], inplace=True)
        df_ = df[["date", "realization"]][df[split] == options[0]].reset_index(
            drop=True
        )
        for name in options:
            part_df = df[colnames][df[split] == name]
            part_df = _rename_columns_figure2(
                part_df,
                mark_choice,
                name,
                colnames,
                containment,
                phases,
            )
            df_ = pandas.concat([df_, part_df], axis=1)
        cols_to_plot, active_cols_at_startup = _make_cols_to_plot(
            split,
            df_,
            containment_info,
        )
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
            # NBNB-AS: Check this, mypy complains:
            args = {
                "line_dash": value[1],
                "marker_color": value[2],
                "legendgroup": col,
                "name": col,
                "customdata": prop,  # type: ignore
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
