import pandas
import pathlib
import numpy as np
from typing import Optional
from enum import Enum


FAULT_POLYGON_ATTRIBUTE = "dl_extracted_faultlines"


class MapAttribute(Enum):
    # TODO: change to upper case
    MigrationTime = "migration-time"
    MaxSaturation = "max-saturation"


def _read_co2_volumes(ensemble_paths):
    records = []
    for ens in ensemble_paths:
        try:
            df = pandas.read_csv(
                pathlib.Path(ens) / "share" / "results" / "tables" / "co2_volumes.csv",
            )
        except FileNotFoundError:
            continue
        last = df.iloc[np.argmax(df["date"])]
        label = pathlib.Path(ens).name
        records += [
            (label, last["co2_inside"], "inside"),
            (label, last["co2_outside"], "outside"),
        ]
    return pandas.DataFrame.from_records(records, columns=["ensemble", "volume", "containment"])


def generate_co2_volume_figure(ensemble_paths, height):
    import plotly.express as px
    df = _read_co2_volumes(ensemble_paths)
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
