from typing import Callable, List

import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc


def line_traces_view(
    get_uuid: Callable,
) -> html.Div:

    return html.Div(
        className="framed",
        style={"fontSize": "0.8em"},
        children=[
            html.H5("Plot traces"),
            html.Div(
                style={"marginTop": "5px", "marginBottom": "5px"},
                children=dcc.RadioItems(
                    id=get_uuid("mode"),
                    options=[
                        {"value": "lines", "label": "Lines"},
                        {"value": "markers", "label": "Points"},
                    ],
                    value="lines",
                    labelStyle={"display": "inline-block"},
                ),
            ),
            dcc.Checklist(
                id=get_uuid("traces"),
                options=[
                    {"label": val, "value": val}
                    for val in ["Realizations", "Mean", "P10/P90", "Low/High"]
                ],
                value=["Realizations"],
                labelStyle={"display": "block"},
                persistence=True,
                persistence_type="session",
            ),
            dcc.Checklist(
                id=get_uuid("observations"),
                options=[{"label": val, "value": val} for val in ["Observations"]],
                value=["Observations"],
                labelStyle={"display": "block"},
                persistence=True,
                persistence_type="session",
            ),
            html.Label(id=get_uuid("statistics_warning"), children=""),
        ],
    )


def highlight_realizations_view(
    get_uuid: Callable, realizations: List[int]
) -> html.Div:

    return html.Div(
        className="framed",
        style={"fontSize": "0.8em"},
        children=[
            html.H5("Highlight realizations"),
            html.Div(
                children=[
                    wcc.Select(
                        style={"width": "25%"},
                        id=get_uuid("highlight-realizations"),
                        options=[{"label": val, "value": val} for val in realizations],
                        value=None,
                        persistence=True,
                        persistence_type="session",
                    ),
                    html.Button(
                        id=get_uuid("clear-highlight-realizations"), children="Clear"
                    ),
                ]
            ),
        ],
    )
