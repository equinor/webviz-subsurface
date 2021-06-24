from typing import TYPE_CHECKING

import dash_html_components as html
import webviz_core_components as wcc

from .selector_view import (
    ensemble_selector,
    property_selector,
    filter_selector,
    source_selector,
)

if TYPE_CHECKING:
    # pylint: disable=cyclic-import
    from ..property_statistics import PropertyStatistics


def selector_view(parent: "PropertyStatistics") -> html.Div:
    return [
        wcc.Selectors(
            label="Selectors",
            children=[
                ensemble_selector(parent=parent, tab="qc", multi=True),
                source_selector(parent=parent, tab="qc"),
                property_selector(parent=parent, tab="qc"),
            ],
        ),
        wcc.Selectors(
            label="Filters",
            children=filter_selector(
                parent=parent,
                tab="qc",
                value="Total" if parent.pmodel.selectors_has_value("Total") else None,
            ),
        ),
    ]


def property_qc_view(parent: "PropertyStatistics") -> wcc.FlexBox:
    return wcc.FlexBox(
        style={"margin": "20px"},
        children=[
            wcc.FlexColumn(
                children=wcc.Frame(
                    style={"height": "80vh", "overflowY": "auto"},
                    children=selector_view(parent=parent),
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
                                    id=parent.uuid("property-qc-plot-type"),
                                    options=[
                                        {"label": "Histograms", "value": "histogram"},
                                        {
                                            "label": "Bar per realization",
                                            "value": "bar",
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
                                    value="histogram",
                                    labelStyle={
                                        "display": "inline-block",
                                        "margin": "5px",
                                    },
                                ),
                            ]
                        ),
                        html.Div(
                            style={"height": "75vh"},
                            id=parent.uuid("property-qc-wrapper"),
                        ),
                    ],
                ),
            ),
        ],
    )
