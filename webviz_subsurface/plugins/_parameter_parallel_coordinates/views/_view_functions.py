import numpy as np
import pandas as pd
from webviz_config import WebvizConfigTheme


# pylint: disable=too-many-arguments
def render_parcoord(
    plot_df: pd.DataFrame,
    theme: WebvizConfigTheme,
    colormap: list,
    color_col: str,
    ens: list,
    mode: str,
    params: list,
    response: str,
    remove_constant: str,
):
    """Renders parallel coordinates plot"""

    dimensions = []
    dimentions_params = []

    if remove_constant == ["remove_constant"]:
        for param in params:
            if len(np.unique(plot_df[param].values)) > 1:
                dimentions_params.append(param)

        dimensions = [
            {"label": param, "values": plot_df[param].values.tolist()}
            for param in dimentions_params
        ]

    else:
        dimensions = [
            {"label": param, "values": plot_df[param].values.tolist()}
            for param in params
        ]

    colormap = (
        colormap if mode == "ensemble" else theme.plotly_theme["layout"]["colorway"]
    )
    if response:
        response = f"Response: {response}"
        params = [response] + params
    # Create parcoords dimensions (one per parameter)
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
