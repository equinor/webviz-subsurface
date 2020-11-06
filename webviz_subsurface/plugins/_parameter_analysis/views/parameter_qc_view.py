import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc


from .selector_view import (
    ensemble_selector,
    filter_parameter,
    html_details,
    sortby_selector,
)


def selector_view(parent) -> html.Div:
    return html.Div(
        className="framed",
        style={"height": "80vh", "overflowY": "auto", "font-size": "15px"},
        children=[
            html.Div(
                children=[
                    html_details(
                        summary="Selections",
                        children=[
                            ensemble_selector(
                                parent=parent,
                                tab="qc",
                                id_string="ensemble-selector",
                                heading="Ensemble A:",
                                value=parent.pmodel.ensembles[0],
                            ),
                            ensemble_selector(
                                parent=parent,
                                tab="qc",
                                id_string="delta-ensemble-selector",
                                heading="Ensemble B:",
                                value=parent.pmodel.ensembles[-1],
                            ),
                            sortby_selector(parent=parent, value="Name"),
                            filter_parameter(
                                parent=parent,
                                tab="qc",
                                value=[parent.pmodel.parameters[0]],
                            ),
                        ],
                        open_details=True,
                    )
                ]
            )
        ],
    )


def parameter_qc_view(parent) -> wcc.FlexBox:
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
                                    {
                                        "label": "Distribution plots",
                                        "value": "distribution",
                                    },
                                    {"label": "Statistics table", "value": "table"},
                                ],
                                value="distribution",
                                labelStyle={
                                    "display": "inline-block",
                                    "margin": "5px",
                                },
                            )
                        ]
                    ),
                    html.Div(
                        style={"height": "75vh"}, id=parent.uuid("property-qc-wrapper")
                    ),
                ],
            ),
        ],
    )
