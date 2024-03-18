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
    ContainmentViews,
    PhaseOptions,
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


_PHASE_DICT = {
    PhaseOptions.TOTAL: "total",
    PhaseOptions.AQUEOUS: "aqueous",
    PhaseOptions.GAS: "gas",
}


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
    view = containment_info["containment_view"]
    if view == ContainmentViews.ZONESPLIT:
        return (
            df[df["zone"] != "all"]
            .drop(columns="region", errors="ignore")
            .reset_index(drop=True)
        )
    if view == ContainmentViews.REGIONSPLIT:
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


def _split_colors(num_cols: int, split: str = "zone") -> List[str]:
    options = list(_COLOR_ZONES)
    if split == "region":
        options.reverse()
    if len(options) >= num_cols:
        return options[:num_cols]
    num_lengths = int(np.ceil(num_cols / len(options)))
    new_cols = options * num_lengths
    return new_cols[:num_cols]


def _prepare_pattern_and_color_options(
    containment_info: Dict,
    split: str,
) -> Tuple[Dict, List, List]:
    options = containment_info[f"{split}s"]
    num_options = len(options)
    if containment_info["ordering"] == 0:
        cat_ord = {
            "type": [
                ", ".join((zn, cn))
                for zn in options
                for cn in ["contained", "outside", "hazardous"]
            ],
        }
        colors = [c for c in _split_colors(num_options, split) for _ in range(3)]
        pattern = ["", "/", "x"] * num_options
    elif containment_info["ordering"] == 1:
        cat_ord = {
            "type": [
                ", ".join((zn, cn))
                for cn in ["contained", "outside", "hazardous"]
                for zn in options
            ],
        }
        colors = [c for _ in range(3) for c in _split_colors(num_options, split)]
        pattern = [""] * num_options
        pattern += ["/"] * num_options
        pattern += ["x"] * num_options
    else:
        cat_ord = {
            "type": [
                ", ".join((zn, cn))
                for cn in ["hazardous", "outside", "contained"]
                for zn in options
            ],
        }
        colors = [
            c
            for c in [_COLOR_HAZARDOUS, _COLOR_OUTSIDE, _COLOR_CONTAINED]
            for _ in range(num_options)
        ]
        base_pattern = ["", "/", "x", "-", "\\", "+", "|", "."]
        if num_options > len(base_pattern):
            base_pattern *= int(np.ceil(num_options / len(base_pattern)))
            warnings.warn(
                f"More {split}s than pattern options. "
                f"Some {split}s will share pattern."
            )
        pattern = base_pattern[:num_options] * 3
    return cat_ord, colors, pattern


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
    view = containment_info["containment_view"]
    records: Dict[str, List[Any]] = {
        "real": [],
        "amount": [],
        "sort_key": [],
        "sort_key_secondary": [],
    }
    if view == ContainmentViews.ZONESPLIT:
        records["zone"] = []
        records["containment"] = []
    elif view == ContainmentViews.REGIONSPLIT:
        records["region"] = []
        records["containment"] = []
    else:
        records["containment"] = []
        records["phase"] = []
    scale_factor = _find_scale_factor(table_provider, scale)
    for real in realizations:
        df = _read_dataframe(table_provider, real, scale_factor, containment_info)
        if view != ContainmentViews.CONTAINMENTSPLIT:
            split = "zone" if view == ContainmentViews.ZONESPLIT else "region"
            phase = containment_info["phase"]
            assert isinstance(phase, str)
            last_ = df[df["date"] == np.max(df["date"])]
            for i in range(last_.shape[0]):
                last = last_.iloc[i]
                label = str(real)

                records["real"] += [label] * 3
                records["amount"] += [
                    last["_".join((_PHASE_DICT[phase], "contained"))],
                    last["_".join((_PHASE_DICT[phase], "outside"))],
                    last["_".join((_PHASE_DICT[phase], "hazardous"))],
                ]
                records["containment"] += ["contained", "outside", "hazardous"]
                records[split] += [last[split]] * 3
                records["sort_key"] += [label] * 3
                records["sort_key_secondary"] += [last[split]] * 3
        else:
            last = df.iloc[np.argmax(df["date"])]
            label = str(real)

            records["real"] += [label] * 6
            records["amount"] += [
                last["aqueous_contained"],
                last["gas_contained"],
                last["aqueous_outside"],
                last["gas_outside"],
                last["aqueous_hazardous"],
                last["gas_hazardous"],
            ]
            records["containment"] += [
                "contained",
                "contained",
                "outside",
                "outside",
                "hazardous",
                "hazardous",
            ]
            records["phase"] += ["aqueous", "gas", "aqueous", "gas", "aqueous", "gas"]
            records["sort_key"] += [last["gas_hazardous"]] * 6
            records["sort_key_secondary"] += [last["gas_outside"]] * 6
    df = pandas.DataFrame.from_dict(records)
    df.sort_values(
        ["sort_key", "sort_key_secondary"], inplace=True, ascending=[True, True]
    )
    return df


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
    df["type"] = df["type"].replace("total", "Total")
    df["type"] = df["type"].replace("total_contained", "Contained")
    df["type"] = df["type"].replace("total_outside", "Outside")
    df["type"] = df["type"].replace("total_hazardous", "Hazardous")
    df["type"] = df["type"].replace("total_gas", "Gas")
    df["type"] = df["type"].replace("total_aqueous", "Aqueous")
    df["type"] = df["type"].replace("gas_contained", "Contained mobile gas")
    df["type"] = df["type"].replace("gas_outside", "Outside mobile gas")
    df["type"] = df["type"].replace("gas_hazardous", "Hazardous mobile gas")
    df["type"] = df["type"].replace("aqueous_contained", "Contained aqueous")
    df["type"] = df["type"].replace("aqueous_outside", "Outside aqueous")
    df["type"] = df["type"].replace("aqueous_hazardous", "Hazardous aqueous")


def _adjust_figure(fig: go.Figure) -> None:
    fig.layout.title.x = 0.5
    fig.layout.paper_bgcolor = "rgba(0,0,0,0)"
    fig.layout.margin.b = 6
    fig.layout.margin.t = 40
    fig.layout.margin.l = 10
    fig.layout.margin.r = 10


def generate_co2_volume_figure(
    table_provider: EnsembleTableProvider,
    realizations: List[int],
    scale: Union[Co2MassScale, Co2VolumeScale],
    containment_info: Dict[str, Any],
) -> go.Figure:
    df = _read_terminal_co2_volumes(
        table_provider, realizations, scale, containment_info
    )
    view = containment_info["containment_view"]
    if view != ContainmentViews.CONTAINMENTSPLIT:
        split = "zone" if view == ContainmentViews.ZONESPLIT else "region"
        color = "type"
        pattern_shape = "type"  # ['', '/', '\\', 'x', '-', '|', '+', '.'],
        cat_ord, colors, pattern = _prepare_pattern_and_color_options(
            containment_info,
            split,
        )

        df["type"] = [
            ", ".join((zn, cn)) for zn, cn in zip(df[split], df["containment"])
        ]
    else:
        color = "containment"
        cat_ord = {
            "containment": ["hazardous", "outside", "contained"],
            "phase": ["gas", "aqueous"],
        }
        colors = [_COLOR_HAZARDOUS, _COLOR_OUTSIDE, _COLOR_CONTAINED]
        pattern_shape = "phase"
        pattern = ["", "/"]
    df["prop"] = np.zeros(df.shape[0])
    for r in realizations:
        summed_amount = np.sum(df.loc[df["real"] == str(r)]["amount"])
        df.loc[df["real"] == str(r), "prop"] = summed_amount
    df["prop"] = np.round(df["amount"] / df["prop"] * 1000) / 10
    df["prop"] = df["prop"].map(lambda p: str(p) + "%")
    fig = px.bar(
        df,
        y="real",
        x="amount",
        color=color,
        pattern_shape=pattern_shape,
        pattern_shape_sequence=pattern,
        title="End-state CO<sub>2</sub> containment (all realizations)",
        orientation="h",
        category_orders=cat_ord,
        color_discrete_sequence=colors,
        hover_data={"prop": True, "real": False},
    )
    fig.layout.legend.title.text = ""
    fig.layout.legend.orientation = "h"
    fig.layout.legend.y = -0.3
    fig.layout.legend.font = {"size": 8}
    fig.layout.yaxis.title = "Realization"
    fig.layout.xaxis.exponentformat = "power"
    fig.layout.xaxis.title = scale.value
    _adjust_figure(fig)
    return fig


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
    view = containment_info["containment_view"]
    if view != ContainmentViews.CONTAINMENTSPLIT:
        split = "zone" if view == ContainmentViews.ZONESPLIT else "region"
        phase = containment_info["phase"]
        containments = ["contained", "outside", "hazardous"]
        df = df.drop(
            columns=[
                "_".join((_PHASE_DICT[p], c))
                for c in containments
                for p in PhaseOptions
                if p != phase
            ]
        )
        df = df.rename(
            columns={
                cn: cn.split("_")[1]
                for cn in ["_".join((_PHASE_DICT[phase], c)) for c in containments]
            }
        )
        df = df.drop(columns=["total_gas", "total_aqueous"])
        df = pandas.melt(df, id_vars=["date", split])
        df["variable"] = df[split] + ", " + df["variable"]
        df = df.drop(columns=[split])
        cat_ord, colors, pattern = _prepare_pattern_and_color_options(
            containment_info,
            split,
        )
    else:
        df = df.drop(
            columns=[
                "total_contained",
                "total_outside",
                "total_hazardous",
                "total_gas",
                "total_aqueous",
            ]
        )
        df = pandas.melt(df, id_vars=["date"])
        cat_ord = {
            "type": [
                "Hazardous mobile gas",
                "Hazardous aqueous",
                "Outside mobile gas",
                "Outside aqueous",
                "Contained mobile gas",
                "Contained aqueous",
            ]
        }
        pattern = ["", "/"] * 3
        colors = [
            _COLOR_HAZARDOUS,
            _COLOR_HAZARDOUS,
            _COLOR_OUTSIDE,
            _COLOR_OUTSIDE,
            _COLOR_CONTAINED,
            _COLOR_CONTAINED,
        ]
    df = df.rename(columns={"value": "mass", "variable": "type"})
    df.sort_values(by="date", inplace=True)
    _change_type_names(df)
    if y_limits[0] is None and y_limits[1] is not None:
        y_limits[0] = 0.0
    elif y_limits[1] is None and y_limits[0] is not None:
        y_limits[1] = max(df.groupby("date")["mass"].sum()) * 1.05
    df["prop"] = np.zeros(df.shape[0])
    for d in np.unique(df["date"]):
        df.loc[df["date"] == d, "prop"] = np.sum(df.loc[df["date"] == d]["mass"])
    df["prop"] = np.round(df["mass"] / df["prop"] * 1000) / 10
    df["prop"] = df["prop"].map(lambda p: str(p) + "%")
    fig = px.area(
        df,
        x="date",
        y="mass",
        color="type",
        category_orders=cat_ord,
        color_discrete_sequence=colors,
        pattern_shape="type",
        pattern_shape_sequence=pattern,  # ['', '/', '\\', 'x', '-', '|', '+', '.'],
        range_y=y_limits,
        hover_data=["prop"],
    )
    fig.layout.yaxis.range = y_limits
    fig.layout.legend.orientation = "h"
    fig.layout.legend.title.text = ""
    fig.layout.legend.y = -0.3
    fig.layout.legend.font = {"size": 8}
    fig.layout.title = "CO<sub>2</sub> containment for realization: " + str(
        time_series_realization
    )
    fig.layout.xaxis.title = "Time"
    fig.layout.yaxis.title = scale.value
    fig.layout.yaxis.exponentformat = "power"
    _adjust_figure(fig)
    return fig


def _prepare_time_figure_options(
    df: pandas.DataFrame,
    containment_info: Dict[str, Any],
) -> Tuple[pandas.DataFrame, Dict[str, Tuple[str, str, str]], List[str]]:
    if containment_info["containment_view"] != ContainmentViews.CONTAINMENTSPLIT:
        colnames = [
            "_".join((_PHASE_DICT[containment_info["phase"]], con))
            for con in ["contained", "outside", "hazardous"]
        ]
        split = (
            "zone"
            if containment_info["containment_view"] == ContainmentViews.ZONESPLIT
            else "region"
        )
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
        if containment_info["ordering"] < 2:
            colors = _split_colors(len(options), split)
            cols_to_plot = {}
            for con, line_type in zip(
                ["contained", "outside", "hazardous"], ["solid", "dot", "dash"]
            ):
                for name, col in zip(options, colors):
                    cols_to_plot[", ".join((name, con))] = (
                        ", ".join((name, con)),
                        line_type,
                        col,
                    )
        else:
            colors = [_COLOR_CONTAINED, _COLOR_OUTSIDE, _COLOR_HAZARDOUS]
            line_types = [
                f"{round(i / len(options) * 25)}px" for i in range(len(options))
            ]
            if len(options) > 8:
                warnings.warn(
                    f"Large number of {split}s might make it hard "
                    f"to distinguish different dashed lines."
                )
            cols_to_plot = {}
            for con, col in zip(["contained", "outside", "hazardous"], colors):
                for name, line_type in zip(options, line_types):
                    cols_to_plot[", ".join((name, con))] = (
                        ", ".join((name, con)),
                        line_type,
                        col,
                    )
        active_cols_at_startup = [name + ", contained" for name in options]
        df = df_
        df["total"] = df[cols_to_plot.keys()].sum(axis=1)
    else:
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
    return df, cols_to_plot, active_cols_at_startup


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
            args = {
                "line_dash": value[1],
                "marker_color": value[2],
                "legendgroup": col,
                "name": col,
                "customdata": np.round(sub_df[value[0]] / sub_df["total"] * 1000) / 10,
            }
            if col not in active_cols_at_startup:
                args["visible"] = "legendonly"
            fig.add_scatter(y=sub_df[value[0]], **args, **common_args)
    fig.layout.legend.orientation = "h"
    fig.layout.legend.title.text = ""
    fig.layout.legend.y = -0.3
    fig.layout.legend.font = {"size": 8}
    fig.layout.legend.tracegroupgap = 0
    fig.layout.title = "CO<sub>2</sub> containment (all realizations)"
    fig.layout.xaxis.title = "Time"
    fig.layout.yaxis.title = scale.value
    fig.layout.yaxis.exponentformat = "power"
    fig.layout.yaxis.autorange = True
    _adjust_figure(fig)
    # fig.update_layout(legend=dict(font=dict(size=8)), legend_tracegroupgap=0)
    return fig
