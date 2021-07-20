from typing import Callable

import webviz_core_components as wcc


def selections_layout(get_uuid: Callable, ensembles: list) -> wcc.Frame:
    return wcc.Frame(
        style={"height": "80vh"},
        children=[
            plot_controls(get_uuid("plot_controls"), ensembles),
            pressure_plot_options(get_uuid("pressure_plot_options")),
        ],
    )


def plot_controls(uuid, ensembles: list) -> wcc.Selectors:
    return wcc.Selectors(
        label="Plot Controls",
        children=[
            wcc.Dropdown(
                label="Ensemble",
                id={"id": uuid, "element": "ensemble"},
                options=[{"label": col, "value": col} for col in ensembles],
                value=ensembles[0],
                multi=False,
            ),
            wcc.RadioItems(
                label="Node type",
                id={"id": uuid, "element": "node_type"},
                options=[
                    {
                        "label": "Well",
                        "value": "well",
                    },
                    {
                        "label": "Field / Group",
                        "value": "field_group",
                    },
                ],
                value="well",
            ),
            wcc.Dropdown(
                label="Node",
                id={"id": uuid, "element": "node"},
                options=[],
                value=None,
                multi=False,
            ),
        ],
    )


def pressure_plot_options(uuid) -> wcc.Selectors:
    """Description"""
    return wcc.Selectors(
        label="Pressure Plot Options",
        children=[
            wcc.Checklist(
                id={"id": uuid, "element": "include_bhp"},
                options=[{"label": "Include BHP", "value": "include_bhp"}],
                value=["include_bhp"],
                # style={"margin-bottom":"1vh"}
            ),
            wcc.RadioItems(
                label="Mean or realization",
                id={"id": uuid, "element": "mean_or_single_real"},
                options=[
                    {
                        "label": "Plot mean",
                        "value": "plot_mean",
                    },
                    {
                        "label": "Single realization",
                        "value": "single_real",
                    },
                ],
                value="plot_mean",
            ),
            wcc.Dropdown(
                id={"id": uuid, "element": "realization"},
                options=[],
                value=None,
                multi=False,
            ),
        ],
    )
