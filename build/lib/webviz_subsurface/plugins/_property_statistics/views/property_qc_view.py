from typing import Callable

import webviz_core_components as wcc
from dash import html

from ..models import PropertyStatisticsModel
from .selector_view import (
    ensemble_selector,
    filter_selector,
    property_selector,
    source_selector,
)


def selector_view(
    get_uuid: Callable, property_model: PropertyStatisticsModel
) -> html.Div:
    return [
        wcc.Selectors(
            label="Selectors",
            children=[
                ensemble_selector(
                    get_uuid=get_uuid,
                    ensembles=property_model.ensembles,
                    tab="qc",
                    multi=True,
                ),
                source_selector(
                    get_uuid=get_uuid, sources=property_model.sources, tab="qc"
                ),
                property_selector(
                    get_uuid=get_uuid, properties=property_model.properties, tab="qc"
                ),
            ],
        ),
        wcc.Selectors(
            label="Plot options",
            children=wcc.Checklist(
                id=get_uuid("property-qc-axis-match"),
                options=[{"label": "Shared plot axis", "value": "shared_axis"}],
                value=[],
            ),
        ),
        wcc.Selectors(
            label="Filters",
            children=filter_selector(
                get_uuid=get_uuid,
                property_model=property_model,
                tab="qc",
                value="Total" if property_model.selectors_has_value("Total") else None,
            ),
        ),
    ]


def property_qc_view(
    get_uuid: Callable, property_model: PropertyStatisticsModel
) -> wcc.FlexBox:
    return wcc.FlexBox(
        style={"margin": "20px"},
        children=[
            wcc.FlexColumn(
                children=wcc.Frame(
                    style={"height": "80vh", "overflowY": "auto"},
                    children=selector_view(
                        get_uuid=get_uuid, property_model=property_model
                    ),
                )
            ),
            wcc.FlexColumn(
                flex=8,
                children=wcc.Frame(
                    color="white",
                    highlight=False,
                    style={"height": "80vh"},
                    children=[
                        wcc.FlexBox(
                            children=[
                                wcc.RadioItems(
                                    vertical=False,
                                    id=get_uuid("property-qc-plot-type"),
                                    options=[
                                        {
                                            "label": "Distributions",
                                            "value": "distribution",
                                        },
                                        {
                                            "label": "Point per realization",
                                            "value": "scatter",
                                        },
                                        {
                                            "label": "Point per realization (single plot)",
                                            "value": "scatter_ensemble",
                                        },
                                        {"label": "Statistics table", "value": "table"},
                                    ],
                                    value="distribution",
                                    labelStyle={
                                        "display": "inline-block",
                                        "margin": "5px",
                                    },
                                ),
                            ]
                        ),
                        html.Div(
                            style={"height": "75vh"},
                            id=get_uuid("property-qc-wrapper"),
                        ),
                    ],
                ),
            ),
        ],
    )
