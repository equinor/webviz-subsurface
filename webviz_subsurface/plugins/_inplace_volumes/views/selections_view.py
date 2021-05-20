from typing import Callable, List

import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc


def selections_layout(
    uuid: Callable,
    volumemodel,
) -> html.Div:
    """Layout for selecting intersection data"""
    return html.Div(
        children=[
            button(uuid=uuid, title="1 plot / 1 table"),
            button(uuid=uuid, title="Plots per zone/region"),
            button(uuid=uuid, title="Custom plotting"),
            html.Div(
                className="webviz-inplace-vol-plotselect",
                children=selector_dropdowns(
                    uuid=uuid,
                    volumemodel=volumemodel,
                ),
            ),
            plot_settings_layout(uuid, volumemodel),
        ]
    )


def button(uuid: str, title: str) -> html.Div:
    return html.Button(
        title,
        className="webviz-inplace-vol-btn",
        id={"id": uuid, "button": title},
    )


def source_selector(uuid: str, volumemodel) -> html.Div:
    sources = volumemodel.sources
    return html.Div(
        style={
            "marginTop": "5px",
        },
        children=html.Label(
            children=[
                html.Span("Source", style={"font-weight": "bold"}),
                dcc.Dropdown(
                    id={"id": uuid, "element": "ensembles"},
                    options=[{"label": source, "value": source} for source in sources],
                    value=sources[0],
                    clearable=False,
                    persistence=True,
                    persistence_type="session",
                ),
            ]
        ),
    )


def selector_dropdowns(uuid: str, volumemodel):
    """Makes dropdowns for each selector"""

    dropdowns: List[html.Div] = []

    for selector in [
        "Plot type",
        "Table type",
        "X Response",
        "Y Response",
        "Subplots",
        "Color by",
    ]:
        if selector == "Plot type":
            elements = ["histogram", "scatter", "distribution", "bar", "box"]
            value = elements[0]
        if selector == "Table type":
            elements = ["Statistics table", "Data table"]
            value = elements[0]
        if selector == "X Response":
            elements = volumemodel.responses
            value = "STOIIP_OIL"
        if selector == "Y Response":
            elements = volumemodel.responses + volumemodel.selectors
            value = "BULK_OIL"
        if selector == "Subplots":
            elements = volumemodel.selectors
            value = None
        if selector == "Color by":
            elements = volumemodel.selectors + [
                x for x in volumemodel.parameters if x not in volumemodel.selectors
            ]
            value = "ENSEMBLE"

        dropdowns.append(
            html.Div(
                html.Label(
                    children=[
                        html.Summary(selector, style={"font-weight": "bold"}),
                        dcc.Dropdown(
                            id={"id": uuid, "selector": selector},
                            options=[{"label": elm, "value": elm} for elm in elements],
                            value=value,
                            clearable=selector in ["Subplots", "Color by"],
                            persistence=True,
                            persistence_type="session",
                        ),
                    ],
                )
            )
        )
    return dropdowns


def plot_settings_layout(uuid: str, volumemodel) -> html.Div:
    return html.Details(
        className="webviz-structunc-settings",
        open=False,
        children=[
            html.Summary(
                style={
                    "font-size": "15px",
                    "font-weight": "bold",
                },
                children="⚙️ Settings",
            ),
            html.Div(
                style={"padding": "10px"},
                children=[
                    subplot_xaxis_range(
                        uuid=uuid,
                        volumemodel=volumemodel,
                    ),
                ],
            ),
        ],
    )


def subplot_xaxis_range(
    uuid: str,
    volumemodel,
) -> html.Div:

    return html.Div(
        children=[
            html.Span("Subplot X axis option", style={"font-weight": "bold"}),
            html.Div(
                style={"backgroumd-color": "white"},
                children=dcc.RadioItems(
                    id={
                        "id": uuid,
                        "settings": "xrange_subplots_matches",
                    },
                    options=[
                        {
                            "label": "Equal range",
                            "value": True,
                        },
                        {
                            "label": "Individual range",
                            "value": False,
                        },
                    ],
                    labelStyle={
                        #        "display": "inline-block",
                        "margin-right": "5px",
                    },
                    value=True,
                ),
            ),
        ]
    )
