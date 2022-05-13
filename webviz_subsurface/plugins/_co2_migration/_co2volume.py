import itertools
import pathlib
from enum import Enum
from typing import Dict
import pandas
import numpy as np


class _Columns(Enum):
    REALIZATION = "realization"
    VOLUME = "volume"
    CONTAINMENT = "containment"
    VOLUME_OUTSIDE = "volume_outside"


def _read_dataframe(realization_path: str):
    return pandas.read_csv(
        pathlib.Path(realization_path) / "share" / "results" / "tables" / "co2_volumes.csv",
    )


def _read_terminal_co2_volumes(realization_paths: Dict[str, str]):
    records = []
    for rz_name, rz_path in realization_paths.items():
        try:
            df = _read_dataframe(rz_path)
        except FileNotFoundError:
            continue
        last = df.iloc[np.argmax(df["date"])]
        label = str(rz_name)
        records += [
            (label, last["co2_inside"], "inside", 0.0),
            (label, last["co2_outside"], "outside", last["co2_outside"]),
        ]
    df = pandas.DataFrame.from_records(
        records,
        columns=[_Columns.REALIZATION, _Columns.VOLUME, _Columns.CONTAINMENT, _Columns.VOLUME_OUTSIDE]
    )
    df.sort_values(_Columns.VOLUME_OUTSIDE, inplace=True, ascending=False)
    return df


def _read_co2_volumes(realization_paths: Dict[str, str]):
    return pandas.concat([
        _read_dataframe(rz_path).assign(realization=rz_name)
        for rz_name, rz_path in realization_paths.items()
    ])


def generate_co2_volume_figure(realization_paths: Dict[str, str], height, width):
    import plotly.express as px
    df = _read_terminal_co2_volumes(realization_paths)
    fig = px.bar(df, y=_Columns.REALIZATION, x=_Columns.VOLUME, color=_Columns.CONTAINMENT, title="End-state CO2 containment", orientation="h")
    # TODO: figure height or yrange should depend on number of realizations (?)
    fig.layout.height = height
    fig.layout.width = width
    fig.layout.legend.title.text = ""
    fig.layout.legend.orientation = "h"
    fig.layout.legend.y = -0.3
    fig.layout.yaxis.title = "Realization"
    fig.layout.xaxis.exponentformat = "power"
    fig.layout.xaxis.title = "Volume [m³]"
    fig.layout.paper_bgcolor = "rgba(0,0,0,0)"
    fig.layout.margin.b = 10
    fig.layout.margin.t = 60
    fig.layout.margin.l = 10
    fig.layout.margin.r = 10
    return fig


def generate_co2_time_containment_figure(realization_paths: Dict[str, str], height, width):
    import plotly.graph_objects as go
    import plotly.express as px
    df = _read_co2_volumes(realization_paths)
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
    dummy_args = dict(mode="lines", marker_color="black", hoverinfo='none')
    fig.add_scatter(y=[.0], **dummy_args, **outside_args)
    fig.add_scatter(y=[.0], **dummy_args, **total_args)
    for rz, color in zip(realization_paths.keys(), itertools.cycle(colors)):
        sub_df = df[df["realization"] == rz]
        common_args = dict(
            x=sub_df["dt"],
            hovertemplate="%{x}: %{y}<br>Realization: %{meta[0]}",
            meta=[rz],
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
    fig.layout.yaxis.title = "Volume [m³]"
    fig.layout.height = height
    fig.layout.width = width
    fig.layout.paper_bgcolor = "rgba(0,0,0,0)"
    fig.layout.margin.b = 10
    fig.layout.margin.t = 60
    fig.layout.margin.l = 10
    fig.layout.margin.r = 10
    fig.layout.yaxis.range = (0, 1.05 * df["co2_total"].max())
    return fig
