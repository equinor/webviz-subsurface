import pandas
import numpy as np
import pathlib
from typing import Dict


def _read_co2_volumes(realization_paths: Dict[str, str]):
    records = []
    for rz_name, rz_path in realization_paths.items():
        try:
            df = pandas.read_csv(
                pathlib.Path(rz_path) / "share" / "results" / "tables" / "co2_volumes.csv",
            )
        except FileNotFoundError:
            continue
        last = df.iloc[np.argmax(df["date"])]
        label = str(rz_name)
        records += [
            (label, last["co2_inside"], "inside", 0.0),
            (label, last["co2_outside"], "outside", last["co2_outside"]),
        ]
    df = pandas.DataFrame.from_records(records, columns=["ensemble", "volume", "containment", "volume_outside"])
    df.sort_values("volume_outside", inplace=True, ascending=False)
    return df


def generate_co2_volume_figure(realization_paths: Dict[str, str], height):
    import plotly.express as px
    df = _read_co2_volumes(realization_paths)
    fig = px.bar(df, y="ensemble", x="volume", color="containment", title="End-state CO2 containment [m³]", orientation="h")
    fig.layout.height = height
    fig.layout.legend.title.text = ""
    fig.layout.legend.orientation = "h"
    fig.layout.yaxis.title = ""
    fig.layout.yaxis.tickangle = -90
    fig.layout.xaxis.exponentformat = "power"
    fig.layout.xaxis.title = ""
    fig.layout.paper_bgcolor = "rgba(0,0,0,0)"
    fig.layout.margin.b = 10
    fig.layout.margin.t = 60
    fig.layout.margin.l = 10
    fig.layout.margin.r = 10
    return fig
