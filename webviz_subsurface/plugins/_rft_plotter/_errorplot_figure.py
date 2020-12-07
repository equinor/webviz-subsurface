from typing import Dict, Union

import pandas as pd


def update_errorplot(
    df: pd.DataFrame, enscolors: Dict[str, str]
) -> Dict[
    str, Union[list, dict]
]:  # TODO(Ruben Thoms) Better to make use of a TypedDict here at some point.

    df["RFT_NAME"] = df.agg(
        lambda x: f"{x['WELL']} {int(x['YEAR'])} {x['ZONE']} ({int(x['TVD'])} TVD)",
        axis=1,
    )
    df["DIFFMEAN"] = df.groupby(["WELL", "DATE", "ZONE", "TVD", "ENSEMBLE"])[
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

    return {"data": traces, "layout": layout}
