from typing import Callable

import dash_html_components as html
import webviz_core_components as wcc


def selections_layout(get_uuid: Callable, ensembles: list) -> wcc.Frame:
    """Layout for the component input options"""
    controls_uuid = get_uuid("controls")
    return wcc.Frame(
        id=get_uuid("selections_layout"),
        style={"height": "82vh"},
        children=[
            wcc.Selectors(
                label="Controls",
                children=[
                    wcc.Dropdown(
                        label="Ensemble",
                        id={"id": controls_uuid, "element": "ensemble"},
                        options=[{"label": ens, "value": ens} for ens in ensembles],
                        clearable=False,
                        value=ensembles[0],
                    ),
                    wcc.RadioItems(
                        label="Mean or realization",
                        id={"id": controls_uuid, "element": "mean_or_single_real"},
                        options=[
                            {
                                "label": "Mean of producing real.",
                                "value": "plot_mean",
                            },
                            {
                                "label": "Single realization",
                                "value": "single_real",
                            },
                        ],
                        value="plot_mean",
                    ),
                    html.Div(
                        id={"id": controls_uuid, "element": "single_real_options"},
                        children=[
                            wcc.Dropdown(
                                id={"id": controls_uuid, "element": "realization"},
                                options=[],
                                value=None,
                                multi=False,
                            )
                        ],
                    ),
                ],
            ),
        ],
    )
