from enum import Enum
from typing import Any, Dict, List, Optional, Union

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


def _read_dataframe(
    table_provider: EnsembleTableProvider,
    realization: int,
    scale_factor: float,
) -> pandas.DataFrame:
    df = table_provider.get_column_data(table_provider.column_names(), [realization])
    if scale_factor == 1.0:
        return df
    for col in df.columns:
        if col != "date":
            df[col] /= scale_factor
    return df


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
) -> pandas.DataFrame:
    records: Dict[str, List[Any]] = {
        "real": [],
        "amount": [],
        "containment": [],
        "phase": [],
        "sort_key": [],
        "sort_key_secondary": [],
    }
    scale_factor = _find_scale_factor(table_provider, scale)
    for real in realizations:
        df = _read_dataframe(table_provider, real, scale_factor)
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
) -> pandas.DataFrame:
    scale_factor = _find_scale_factor(table_provider, scale)
    return pandas.concat(
        [
            _read_dataframe(table_provider, real, scale_factor).assign(realization=real)
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
) -> go.Figure:
    df = _read_terminal_co2_volumes(table_provider, realizations, scale)
    fig = px.bar(
        df,
        y="real",
        x="amount",
        color="containment",
        pattern_shape="phase",
        title="End-state CO<sub>2</sub> containment (all realizations)",
        orientation="h",
        category_orders={
            "containment": ["hazardous", "outside", "contained"],
            "phase": ["gas", "aqueous"],
        },
        color_discrete_sequence=[_COLOR_HAZARDOUS, _COLOR_OUTSIDE, _COLOR_CONTAINED],
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
) -> go.Figure:
    df = _read_co2_volumes(table_provider, [time_series_realization], scale)
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
    df = pandas.melt(df, id_vars=["date"])
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
        category_orders={
            "type": [
                "Hazardous mobile gas",
                "Hazardous aqueous",
                "Outside mobile gas",
                "Outside aqueous",
                "Contained mobile gas",
                "Contained aqueous",
            ]
        },
        color_discrete_sequence=[
            _COLOR_HAZARDOUS,
            _COLOR_HAZARDOUS,
            _COLOR_OUTSIDE,
            _COLOR_OUTSIDE,
            _COLOR_CONTAINED,
            _COLOR_CONTAINED,
        ],
        pattern_shape="type",
        pattern_shape_sequence=[
            "",
            "/",
            "",
            "/",
            "",
            "/",
        ],  # ['', '/', '\\', 'x', '-', '|', '+', '.'],
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
    _adjust_figure(fig)
    return fig


def generate_co2_time_containment_figure(
    table_provider: EnsembleTableProvider,
    realizations: List[int],
    scale: Union[Co2MassScale, Co2VolumeScale],
) -> go.Figure:
    df = _read_co2_volumes(table_provider, realizations, scale)
    df.sort_values(by="date", inplace=True)
    fig = go.Figure()
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
    # Generate dummy scatters for legend entries
    dummy_args = {"mode": "lines", "hoverinfo": "none"}
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
    fig.layout.yaxis.exponentformat = "none"
    fig.layout.yaxis.range = (0, 1.05 * df["total"].max())
    _adjust_figure(fig)
    # fig.update_layout(legend=dict(font=dict(size=8)), legend_tracegroupgap=0)
    return fig
