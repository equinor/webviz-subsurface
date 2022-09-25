from typing import Dict

import pandas as pd
import webviz_core_components as wcc


def update_errorplot(df: pd.DataFrame, enscolors: Dict[str, str]) -> wcc.Graph:
    df["RFT_NAME"] = df.agg(
        lambda x: f"{x['WELL']} {int(x['YEAR'])} {x['ZONE']} ({int(x['MD'])} MD)",
        axis=1,
    )
    df["DIFFMEAN"] = df.groupby(["WELL", "DATE", "ZONE", "MD", "ENSEMBLE"])[
        "ABSDIFF"
    ].transform("median")
    traces = []
    for i, (ensemble, ensdf) in enumerate(df.groupby("ENSEMBLE")):
        if i == 0:
            ensdf = ensdf.sort_values(by=["DIFFMEAN"])
        traces.append(
            {
                "x": ensdf["DIFF"],
                "y": ensdf["RFT_NAME"],
                "name": ensemble,
                "type": "box",
                "orientation": "h",
                "offsetgroup": i,
                "marker": {"color": enscolors[ensemble]},
            }
        )
    layout = {
        "margin": {"l": 250, "r": 0, "b": 50, "t": 100},
        "height": 750,
        "legend": {"orientation": "h"},
        "boxmode": "group",
        "xaxis": {"title": "Difference in bar"},
    }

    return wcc.Graph(
        style={"height": "84vh"}, figure={"data": traces, "layout": layout}
    )
