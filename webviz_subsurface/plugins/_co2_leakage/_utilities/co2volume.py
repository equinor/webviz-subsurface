import itertools
from enum import Enum
from typing import Any, Dict, List

import numpy as np
import pandas
import plotly.express as px
import plotly.graph_objects as go

from webviz_subsurface._providers import EnsembleTableProvider
from webviz_subsurface.plugins._co2_leakage._utilities.generic import Co2Scale


class _Columns(Enum):
    REALIZATION = "realization"
    VOLUME = "volume"
    CONTAINMENT = "containment"
    VOLUME_OUTSIDE = "volume_outside"


def _read_dataframe(
    table_provider: EnsembleTableProvider,
    realization: int,
    scale: Co2Scale,
) -> pandas.DataFrame:
    df = table_provider.get_column_data(table_provider.column_names(), [realization])
    if scale == Co2Scale.KG:
        return df
    if scale == scale.MTONS:
        value = 1e9
    else:
        value = df["total"].max()
    for col in df.columns:
        if col.startswith("total"):
            df[col] /= value
    return df


def _read_terminal_co2_volumes(
    table_provider: EnsembleTableProvider, realizations: List[int], scale: Co2Scale
) -> pandas.DataFrame:
    records: Dict[str, List[Any]] = {
        "real": [],
        "amount": [],
        "containment": [],
        "phase": [],
        "sort_key": [],
    }
    for real in realizations:
        df = _read_dataframe(table_provider, real, scale)
        last = df.iloc[np.argmax(df["date"])]
        label = str(real)
        records["real"] += [label] * 4
        records["amount"] += [
            last["total_aqueous_inside"],
            last["total_gas_inside"],
            last["total_aqueous_outside"],
            last["total_gas_outside"],
        ]
        records["containment"] += ["inside", "inside", "outside", "outside"]
        records["phase"] += ["aqueous", "gas", "aqueous", "gas"]
        records["sort_key"] += [last["total_gas_outside"]] * 4
    df = pandas.DataFrame.from_dict(records)
    df.sort_values("sort_key", inplace=True, ascending=True)
    return df


def _read_co2_volumes(
    table_provider: EnsembleTableProvider, realizations: List[int], scale: Co2Scale
) -> pandas.DataFrame:
    return pandas.concat(
        [
            _read_dataframe(table_provider, real, scale).assign(realization=real)
            for real in realizations
        ]
    )


def _adjust_figure(fig: go.Figure) -> None:
    fig.layout.title.x = 0.5
    fig.layout.paper_bgcolor = "rgba(0,0,0,0)"
    fig.layout.margin.b = 10
    fig.layout.margin.t = 60
    fig.layout.margin.l = 10
    fig.layout.margin.r = 10


def generate_co2_volume_figure(
    table_provider: EnsembleTableProvider,
    realizations: List[int],
    scale: Co2Scale,
) -> go.Figure:
    df = _read_terminal_co2_volumes(table_provider, realizations, scale)
    fig = px.bar(
        df,
        y="real",
        x="amount",
        color="containment",
        pattern_shape="phase",
        title="End-state CO2 containment",
        orientation="h",
        category_orders={
            "containment": ["outside", "inside"],
            "phase": ["gas", "aqueous"],
        },
        color_discrete_sequence=["#dd4300", "#006ddd"],
    )
    fig.layout.legend.title.text = ""
    fig.layout.legend.orientation = "h"
    fig.layout.legend.y = -0.3
    fig.layout.yaxis.title = "Realization"
    fig.layout.xaxis.exponentformat = "power"
    fig.layout.xaxis.title = scale.value
    _adjust_figure(fig)
    return fig


def generate_co2_time_containment_figure(
    table_provider: EnsembleTableProvider,
    realizations: List[int],
    scale: Co2Scale,
) -> go.Figure:
    df = _read_co2_volumes(table_provider, realizations, scale)
    df.sort_values(by="date", inplace=True)
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
            x=sub_df["date"],
            hovertemplate="%{x}: %{y}<br>Realization: %{meta[0]}",
            meta=[rlz],
            marker_color=color,
            showlegend=False,
        )
        fig.add_scatter(y=sub_df["total_outside"], **outside_args, **common_args)
        fig.add_scatter(y=sub_df["total"], **total_args, **common_args)
    fig.layout.legend.orientation = "h"
    fig.layout.legend.title.text = ""
    fig.layout.legend.y = -0.3
    fig.layout.title = "Contained CO2"
    fig.layout.xaxis.title = "Time"
    fig.layout.yaxis.title = scale.value
    fig.layout.yaxis.exponentformat = "none"
    fig.layout.yaxis.range = (0, 1.05 * df["total"].max())
    _adjust_figure(fig)
    return fig


def generate_co2_mobile_phase_figure(
    table_provider: EnsembleTableProvider,
    realizations: List[int],
    scale: Co2Scale,
) -> go.Figure:
    df = _read_co2_volumes(table_provider, realizations, scale)
    df.sort_values(by="date", inplace=True)
    y_col = "total_gas_outside"
    df[df[y_col] < 1e-12] = np.nan
    fig = px.line(df, x="date", y=y_col, line_group="realization")
    fig.layout.title = "Mobile gas outside boundary"
    fig.layout.yaxis.title = scale.value
    fig.layout.yaxis.exponentformat = "none"
    fig.layout.xaxis.title = "Time"
    _adjust_figure(fig)
    return fig
