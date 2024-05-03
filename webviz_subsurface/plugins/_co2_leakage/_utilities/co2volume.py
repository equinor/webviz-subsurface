from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas
import plotly.express as px
import plotly.graph_objects as go

from webviz_subsurface._providers import EnsembleTableProvider
from webviz_subsurface._utils.enum_shim import StrEnum
from webviz_subsurface.plugins._co2_leakage._utilities.generic import (
    Co2MassScale,
    Co2VolumeScale,
    ContainmentViews,
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
    containment_info: Dict[str, Union[str, None, List[str]]],
) -> pandas.DataFrame:
    df = table_provider.get_column_data(table_provider.column_names(), [realization])
    if any(split in list(df.columns) for split in ["zone", "region"]):
        df = _process_containment_information(df, containment_info)
        if containment_info["containment_view"] != ContainmentViews.CONTAINMENTSPLIT:
            df["aqueous"] = (
                df["aqueous_contained"]
                + df["aqueous_outside"]
                + df["aqueous_hazardous"]
            )
            df["gas"] = df["gas_contained"] + df["gas_outside"] + df["gas_hazardous"]
            df = df.drop(
                columns=[
                    "aqueous_contained",
                    "aqueous_outside",
                    "aqueous_hazardous",
                    "gas_contained",
                    "gas_outside",
                    "gas_hazardous",
                ]
            )
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
        "phase": [],
        "sort_key": [],
        "sort_key_secondary": [],
    }
    if view == ContainmentViews.ZONESPLIT:
        records["zone"] = []
    elif view == ContainmentViews.REGIONSPLIT:
        records["region"] = []
    else:
        records["containment"] = []
    scale_factor = _find_scale_factor(table_provider, scale)
    for real in realizations:
        df = _read_dataframe(table_provider, real, scale_factor, containment_info)
        if view != ContainmentViews.CONTAINMENTSPLIT:
            split = "zone" if view == ContainmentViews.ZONESPLIT else "region"
            last_ = df[df["date"] == np.max(df["date"])]
            for i in range(last_.shape[0]):
                last = last_.iloc[i]
                label = str(real)

                records["real"] += [label] * 2
                records["amount"] += [
                    last["aqueous"],
                    last["gas"],
                ]
                records["phase"] += ["aqueous", "gas"]
                records[split] += [last[split]] * 2
                records["sort_key"] += [label] * 2
                records["sort_key_secondary"] += [last[split]] * 2
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
    if containment_info["containment_view"] == ContainmentViews.ZONESPLIT:
        color = "zone"
        cat_ord = {"zone": containment_info["zones"], "phase": ["gas", "aqueous"]}
        colors = _split_colors(len(containment_info["zones"]))
    elif containment_info["containment_view"] == ContainmentViews.REGIONSPLIT:
        color = "region"
        cat_ord = {"region": containment_info["regions"], "phase": ["gas", "aqueous"]}
        colors = _split_colors(len(containment_info["regions"]), "region")
    else:
        color = "containment"
        cat_ord = {
            "containment": ["hazardous", "outside", "contained"],
            "phase": ["gas", "aqueous"],
        }
        colors = [_COLOR_HAZARDOUS, _COLOR_OUTSIDE, _COLOR_CONTAINED]
    fig = px.bar(
        df,
        y="real",
        x="amount",
        color=color,
        pattern_shape="phase",
        title="End-state CO<sub>2</sub> containment (all realizations)",
        orientation="h",
        category_orders=cat_ord,
        color_discrete_sequence=colors,
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
            "total_contained",
            "total_outside",
            "total_hazardous",
            "total_gas",
            "total_aqueous",
        ]
    )
    if containment_info["containment_view"] == ContainmentViews.ZONESPLIT:
        df = pandas.melt(df, id_vars=["date", "zone"])
        df["variable"] = df["zone"] + ", " + df["variable"]
        df = df.drop(columns=["zone"])
        cat_ord = {
            "type": [
                zone_name + ", " + phase
                for zone_name in containment_info["zones"]
                for phase in ["gas", "aqueous"]
            ]
        }
        pattern = ["", "/"] * len(containment_info["zones"])
        colors = [
            col
            for col in _split_colors(len(containment_info["zones"]))
            for i in range(2)
        ]
    elif containment_info["containment_view"] == ContainmentViews.REGIONSPLIT:
        df = pandas.melt(df, id_vars=["date", "region"])
        df["variable"] = df["region"] + ", " + df["variable"]
        df = df.drop(columns=["region"])
        cat_ord = {
            "type": [
                region_name + ", " + phase
                for region_name in containment_info["regions"]
                for phase in ["gas", "aqueous"]
            ]
        }
        pattern = ["", "/"] * len(containment_info["regions"])
        colors = [
            col
            for col in _split_colors(len(containment_info["regions"]), "region")
            for i in range(2)
        ]
    else:
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
    view = containment_info["containment_view"]
    if view != ContainmentViews.CONTAINMENTSPLIT:
        split = "zone" if view == ContainmentViews.ZONESPLIT else "region"
        options = (
            containment_info["zones"]
            if split == "zone"
            else containment_info["regions"]
        )
        df = df.drop(
            columns=[
                "REAL",
                "total_gas",
                "total_aqueous",
                "total_contained",
                "total_outside",
                "total_hazardous",
                "region" if split == "zone" else "zone",
            ],
            errors="ignore",
        )
        df.sort_values(by=["date", "realization"], inplace=True)
        df_ = df[["date", "realization"]][df[split] == options[0]].reset_index(
            drop=True
        )
        for name in options:
            part_df = df[["total", "gas", "aqueous"]][df[split] == name]
            part_df = part_df.rename(
                columns={
                    "total": name + ", total",
                    "gas": name + ", gas",
                    "aqueous": name + ", aqueous",
                }
            ).reset_index(drop=True)
            df_ = pandas.concat([df_, part_df], axis=1)
        colors = _split_colors(len(options), split)
        cols_to_plot = {}
        for phase, line_type in zip(
            ["total", "gas", "aqueous"], ["solid", "dot", "dash"]
        ):
            for name, col in zip(options, colors):
                cols_to_plot[name + ", " + phase] = (
                    name + ", " + phase,
                    line_type,
                    col,
                )
        active_cols_at_startup = [name + ", total" for name in options]
        df = df_
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
        active_cols_at_startup = ["Total", "Outside", "Hazardous"]
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
            "hovertemplate": "%{x}: %{y}<br>Realization: %{meta[0]}",
            "meta": [rlz],
            "showlegend": False,
        }
        for col, value in cols_to_plot.items():
            args = {
                "line_dash": value[1],
                "marker_color": value[2],
                "legendgroup": col,
                "name": col,
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
