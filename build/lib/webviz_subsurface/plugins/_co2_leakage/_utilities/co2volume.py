import itertools
from enum import Enum
from typing import List

import numpy as np
import pandas
import plotly.express as px
import plotly.graph_objects as go

from webviz_subsurface._providers import EnsembleTableProvider


class _Columns(Enum):
    REALIZATION = "realization"
    VOLUME = "volume"
    CONTAINMENT = "containment"
    VOLUME_OUTSIDE = "volume_outside"


def _read_dataframe(
    table_provider: EnsembleTableProvider, realization: int
) -> pandas.DataFrame:
    return table_provider.get_column_data(
        ["date", "co2_inside", "co2_outside"], [realization]
    )


def _read_terminal_co2_volumes(
    table_provider: EnsembleTableProvider, realizations: List[int]
) -> pandas.DataFrame:
    records = []
    for real in realizations:
        df = _read_dataframe(table_provider, real)
        last = df.iloc[np.argmax(df["date"])]
        label = str(real)
        records += [
            (label, last["co2_inside"], "inside", 0.0),
            (label, last["co2_outside"], "outside", last["co2_outside"]),
        ]
    df = pandas.DataFrame.from_records(
        records,
        columns=[
            _Columns.REALIZATION.value,
            _Columns.VOLUME.value,
            _Columns.CONTAINMENT.value,
            _Columns.VOLUME_OUTSIDE.value,
        ],
    )
    df.sort_values(_Columns.VOLUME_OUTSIDE.value, inplace=True, ascending=True)
    return df


def _read_co2_volumes(
    table_provider: EnsembleTableProvider, realizations: List[int]
) -> pandas.DataFrame:
    return pandas.concat(
        [
            _read_dataframe(table_provider, real).assign(realization=real)
            for real in realizations
        ]
    )


def generate_co2_volume_figure(
    table_provider: EnsembleTableProvider,
    realizations: List[int],
) -> go.Figure:
    df = _read_terminal_co2_volumes(table_provider, realizations)
    fig = px.bar(
        df,
        y=_Columns.REALIZATION.value,
        x=_Columns.VOLUME.value,
        color=_Columns.CONTAINMENT.value,
        title="End-state CO2 containment",
        orientation="h",
        category_orders={_Columns.CONTAINMENT.value: ["outside", "inside"]},
        color_discrete_sequence=["#dd4300", "#006ddd"],
    )
    fig.layout.legend.title.text = ""
    fig.layout.legend.orientation = "h"
    fig.layout.legend.y = -0.3
    fig.layout.yaxis.title = "Realization"
    fig.layout.xaxis.exponentformat = "power"
    fig.layout.xaxis.title = "Mass [kg]"
    fig.layout.paper_bgcolor = "rgba(0,0,0,0)"
    fig.layout.margin.b = 10
    fig.layout.margin.t = 60
    fig.layout.margin.l = 10
    fig.layout.margin.r = 10
    return fig


def generate_co2_time_containment_figure(
    table_provider: EnsembleTableProvider,
    realizations: List[int],
) -> go.Figure:
    df = _read_co2_volumes(table_provider, realizations)
    df.sort_values(by="date", inplace=True)
    df["date"] = df["date"].astype(str)
    dates = df["date"].str[:4] + "-" + df["date"].str[4:6] + "-" + df["date"].str[6:]
    df["dt"] = dates
    df["co2_total"] = df["co2_inside"] + df["co2_outside"]
    fig = go.Figure()
    colors = px.colors.qualitative.Plotly
    # Generate dummy scatters for legend entries
    outside_args = dict(line_dash="dot", legendgroup="Outside", name="Outside")
    total_args = dict(legendgroup="Total", name="Total")
    dummy_args = dict(mode="lines", marker_color="black", hoverinfo="none")
    fig.add_scatter(y=[0.0], **dummy_args, **outside_args)
    fig.add_scatter(y=[0.0], **dummy_args, **total_args)
    for rlz, color in zip(realizations, itertools.cycle(colors)):
        sub_df = df[df["realization"] == rlz]
        common_args = dict(
            x=sub_df["dt"],
            hovertemplate="%{x}: %{y}<br>Realization: %{meta[0]}",
            meta=[rlz],
            marker_color=color,
            showlegend=False,
        )
        fig.add_scatter(y=sub_df["co2_outside"], **outside_args, **common_args)
        fig.add_scatter(y=sub_df["co2_total"], **total_args, **common_args)
    fig.layout.legend.orientation = "h"
    fig.layout.legend.title.text = ""
    fig.layout.legend.yanchor = "bottom"
    fig.layout.legend.y = 1.02
    fig.layout.legend.xanchor = "right"
    fig.layout.legend.x = 1
    fig.layout.xaxis.title = "Time (date)"
    fig.layout.yaxis.title = "Mass [kg]"
    fig.layout.paper_bgcolor = "rgba(0,0,0,0)"
    fig.layout.margin.b = 10
    fig.layout.margin.t = 60
    fig.layout.margin.l = 10
    fig.layout.margin.r = 10
    fig.layout.yaxis.range = (0, 1.05 * df["co2_total"].max())
    return fig
