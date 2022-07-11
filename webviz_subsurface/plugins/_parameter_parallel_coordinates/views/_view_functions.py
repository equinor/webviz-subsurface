from typing import List

import pandas as pd
from webviz_config import WebvizConfigTheme


def render_parcoord(
    plot_df: pd.DataFrame,
    theme: WebvizConfigTheme,
    colormap: list,
    color_col: str,
    ens: list,
    mode: str,
    params: list,
    response: str,
):
    """Renders parallel coordinates plot"""
    colormap = (
        colormap if mode == "ensemble" else theme.plotly_theme["layout"]["colorway"]
    )
    if response:
        response = f"Response: {response}"
        params = [response] + params
    # Create parcoords dimensions (one per parameter)
    dimensions = [{"label": param, "values": plot_df[param]} for param in params]
    data = [
        {
            "line": {
                "color": plot_df[color_col].values.tolist(),
                "colorscale": colormap,
                "cmin": -0.5,
                "cmax": len(ens) - 0.5,
                "showscale": True,
                "colorbar": {
                    "tickvals": list(range(0, len(ens))),
                    "ticktext": ens,
                    "title": "Ensemble",
                    "xanchor": "right",
                    "x": -0.02,
                    "len": 0.2 * len(ens),
                },
            },
            "dimensions": dimensions,
            "labelangle": 60,
            "labelside": "bottom",
            "type": "parcoords",
        }
        if mode == "ensemble"
        else {
            "type": "parcoords",
            "line": {
                "color": plot_df[response],
                "colorscale": colormap,
                "showscale": True,
                "colorbar": {
                    "title": {"text": response},
                    "xanchor": "right",
                    "x": -0.02,
                },
            },
            "dimensions": dimensions,
            "labelangle": 60,
            "labelside": "bottom",
        }
        if mode == "response"
        else {}
    ]

    # Ensure sufficient spacing between each dimension and margin for labels
    width = len(dimensions) * 80 + 250
    layout = {"width": width, "height": 1200, "margin": {"b": 740, "t": 30}}
    return {"data": data, "layout": theme.create_themed_layout(layout)}


def remove_constants(df: pd.DataFrame):
    for i in range(len(df.columns)):
        print(i)
