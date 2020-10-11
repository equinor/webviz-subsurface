import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc

from .selector_view import (
    ensemble_selector,
    property_selector,
    filter_selector,
    source_selector,
)


def selector_view(parent) -> html.Div:
    return html.Div(
        className="framed",
        style={"height": "80vh", "overflowY": "auto"},
        children=[
            html.Div(
                children=[
                    ensemble_selector(parent=parent, tab="qc", multi=True),
                ]
            ),
            source_selector(parent=parent, tab="qc"),
            property_selector(parent=parent, tab="qc"),
            filter_selector(
                parent=parent,
                tab="qc",
                value="Total" if parent.pmodel.selectors_has_value("Total") else None,
                open_details=True,
            ),
        ],
    )


def property_qc_view(parent) -> wcc.FlexBox:
    return wcc.FlexBox(
        style={"margin": "20px"},
        children=[
            html.Div(style={"flex": 1}, children=selector_view(parent=parent)),
            html.Div(
                style={"flex": 4, "height": "80vh"},
                className="framed",
                children=[
                    wcc.FlexBox(
                        children=[
                            dcc.RadioItems(
                                id=parent.uuid("property-qc-plot-type"),
                                options=[
                                    {"label": "Histograms", "value": "histogram"},
                                    {"label": "Bar per realization", "value": "bar"},
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
                        style={"height": "75vh"}, id=parent.uuid("property-qc-wrapper")
                    ),
                ],
            ),
        ],
    )
