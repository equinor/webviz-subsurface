from typing import Callable, Dict

import webviz_core_components as wcc
from dash import html

from .._ensemble_well_analysis_data import EnsembleWellAnalysisData
from .._types import PressurePlotMode


# pylint: disable = too-few-public-methods
class WellControlLayoutElements:
    GRAPH = "well-control-graph"
    ENSEMBLE = "well-control-ensemble"
    WELL = "well-control-well"
    INCLUDE_BHP = "well-control-include-bhp"
    PRESSURE_PLOT_MODE = "well-control-pressure-plot-mode"
    SINGLE_REAL_OPTIONS = "well-control-single-real-options"
    REAL = "well-control-real"
    CTRLMODE_BAR = "well-control-ctrlmode-bar"
    SHARED_XAXES = "well-control-shared-xaxes"


def well_control_tab(
    get_uuid: Callable, data_models: Dict[str, EnsembleWellAnalysisData]
) -> wcc.FlexBox:
    return wcc.FlexBox(
        children=[
            controls(get_uuid, data_models),
            wcc.Frame(
                style={"flex": 5, "height": "87vh"},
                color="white",
                highlight=False,
                id=get_uuid(WellControlLayoutElements.GRAPH),
                children=[],
            ),
        ]
    )


def controls(
    get_uuid: Callable, data_models: Dict[str, EnsembleWellAnalysisData]
) -> wcc.Frame:
    ensembles = list(data_models.keys())
    return wcc.Frame(
        style={"flex": 1, "height": "87vh"},
        children=[
            wcc.Selectors(
                label="Plot Controls",
                children=[
                    wcc.Dropdown(
                        label="Ensemble",
                        id=get_uuid(WellControlLayoutElements.ENSEMBLE),
                        options=[{"label": col, "value": col} for col in ensembles],
                        value=ensembles[0],
                        multi=False,
                    ),
                    wcc.Dropdown(
                        label="Well",
                        id=get_uuid(WellControlLayoutElements.WELL),
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
                        id=get_uuid(WellControlLayoutElements.INCLUDE_BHP),
                        options=[{"label": "Include BHP", "value": "include_bhp"}],
                        value=["include_bhp"],
                    ),
                    wcc.RadioItems(
                        label="Mean or realization",
                        id=get_uuid(WellControlLayoutElements.PRESSURE_PLOT_MODE),
                        options=[
                            {
                                "label": "Mean of producing real.",
                                "value": PressurePlotMode.MEAN.value,
                            },
                            {
                                "label": "Single realization",
                                "value": PressurePlotMode.SINGLE_REAL.value,
                            },
                        ],
                        value=PressurePlotMode.MEAN.value,
                    ),
                    html.Div(
                        id=get_uuid(WellControlLayoutElements.SINGLE_REAL_OPTIONS),
                        children=[
                            wcc.Dropdown(
                                id=get_uuid(WellControlLayoutElements.REAL),
                                options=[],
                                value=None,
                                multi=False,
                            ),
                            wcc.Checklist(
                                id=get_uuid(WellControlLayoutElements.CTRLMODE_BAR),
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
                        id=get_uuid(WellControlLayoutElements.SHARED_XAXES),
                        options=[{"label": "Shared x-axis", "value": "shared_xaxes"}],
                        value=["shared_xaxes"],
                    ),
                ],
            ),
        ],
    )
