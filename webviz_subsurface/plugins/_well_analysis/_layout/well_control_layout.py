from typing import Callable, Dict, List

import webviz_core_components as wcc
from dash import html

from .._ensemble_data import EnsembleData

# pylint: disable = too-few-public-methods
class WellControlLayoutElements:
    GRAPH = "well-control-graph"
    ENSEMBLE = "well-control-ensemble"
    WELL = "well-control-well"
    INCLUDE_BHP = "well-control-include-bhp"
    MEAN_OR_REAL = "well-control-mean-or-real"
    SINGLE_REAL_OPTIONS = "well-control-single-real-options"
    REAL = "well-control-real"
    CTRLMODE_BAR = "well-control-ctrlmode-bar"
    SHARED_XAXIS = "well-control-shared-xaxis"


def well_control_tab(
    get_uuid: Callable, data_models: Dict[str, EnsembleData]
) -> wcc.FlexBox:
    return wcc.FlexBox(
        children=[
            controls(get_uuid, data_models),
            wcc.Frame(
                style={"flex": 4, "height": "87vh"},
                color="white",
                highlight=False,
                id=get_uuid(WellControlLayoutElements.GRAPH),
                children=[],
            ),
        ]
    )


def controls(get_uuid: Callable, data_models: Dict[str, EnsembleData]) -> wcc.Frame:
    return wcc.Frame(
        style={"flex": 1, "height": "87vh"},
        children=[
            wcc.Selectors(
                label="Selectors",
                children=[
                    wcc.Dropdown(
                        label="Ensemble",
                        id=WellControlLayoutElements.ENSEMBLE,
                        # options=[{"label": col, "value": col} for col in ensembles],
                        # value=ensembles[0],
                        multi=False,
                    ),
                    wcc.Dropdown(
                        label="Well",
                        id=WellControlLayoutElements.WELL,
                        options=[],
                        value=None,
                        multi=False,
                    ),
                ],
            ),
            wcc.Selectors(
                label="Pressure Plot Options",
                children=[
                    wcc.Checklist(
                        id=WellControlLayoutElements.INCLUDE_BHP,
                        options=[{"label": "Include BHP", "value": "include_bhp"}],
                        value=["include_bhp"],
                    ),
                    wcc.RadioItems(
                        label="Mean or realization",
                        id=WellControlLayoutElements.MEAN_OR_REAL,
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
                        id=WellControlLayoutElements.SINGLE_REAL_OPTIONS,
                        children=[
                            wcc.Dropdown(
                                id=WellControlLayoutElements.REAL,
                                options=[],
                                value=None,
                                multi=False,
                            ),
                            wcc.Checklist(
                                id=WellControlLayoutElements.CTRLMODE_BAR,
                                options=[
                                    {
                                        "label": "Display ctrl mode bar",
                                        "value": "ctrlmode_bar",
                                    }
                                ],
                                value=["ctrlmode_bar"],
                            ),
                        ],
                    ),
                ],
            ),
            wcc.Selectors(
                label="⚙️ Settings",
                children=[
                    wcc.Checklist(
                        id=get_uuid(WellControlLayoutElements.SHARED_XAXIS),
                        options=[{"label": "Shared x-axis", "value": "shared_xaxes"}],
                        value=["shared_xaxes"],
                    ),
                ],
            ),
        ],
    )
