from typing import Callable

import webviz_core_components as wcc
from dash import html

from ..models import ParametersModel
from .selector_view import ensemble_selector, filter_parameter, sortby_selector


def selector_view(get_uuid: Callable, parametermodel: ParametersModel) -> html.Div:
    return html.Div(
        [
            wcc.Selectors(
                label="Ensembles",
                children=[
                    ensemble_selector(
                        get_uuid=get_uuid,
                        ensembles=parametermodel.ensembles,
                        tab="qc",
                        id_string="ensemble-selector",
                        heading="Ensemble A:",
                        value=parametermodel.ensembles[0],
                    ),
                    ensemble_selector(
                        get_uuid=get_uuid,
                        ensembles=parametermodel.ensembles,
                        tab="qc",
                        id_string="delta-ensemble-selector",
                        heading="Ensemble B:",
                        value=parametermodel.ensembles[-1],
                    ),
                ],
            ),
            wcc.Selectors(
                label="Parameters",
                children=[
                    sortby_selector(get_uuid=get_uuid, value="Name"),
                    filter_parameter(
                        get_uuid=get_uuid,
                        parametermodel=parametermodel,
                        tab="qc",
                        value=[parametermodel.parameters[0]],
                    ),
                ],
            ),
        ],
    )


def parameter_qc_view(
    get_uuid: Callable, parametermodel: ParametersModel
) -> wcc.FlexBox:
    return wcc.FlexBox(
        children=[
            wcc.FlexColumn(
                wcc.Frame(
                    style={"height": "80vh"},
                    children=selector_view(
                        get_uuid=get_uuid, parametermodel=parametermodel
                    ),
                ),
            ),
            wcc.FlexColumn(
                flex=4,
                children=wcc.Frame(
                    color="white",
                    highlight=False,
                    style={"height": "80vh"},
                    children=[
                        wcc.RadioItems(
                            vertical=False,
                            id=get_uuid("property-qc-plot-type"),
                            options=[
                                {
                                    "label": "Distribution plots",
                                    "value": "distribution",
                                },
                                {"label": "Box plots", "value": "box"},
                                {"label": "Statistics table", "value": "table"},
                            ],
                            value="distribution",
                        ),
                        html.Div(
                            style={"height": "75vh", "margin-top": "20px"},
                            id=get_uuid("property-qc-wrapper"),
                        ),
                    ],
                ),
            ),
        ],
    )
