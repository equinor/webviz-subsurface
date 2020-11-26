from typing import Union

import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from ..figures.color_figure import color_figure


def ensemble_selector(
    parent,
    tab: str,
    id_string: str,
    multi: bool = False,
    value: str = None,
    heading: str = None,
) -> html.Div:
    children = []
    if heading is not None:
        children.append(html.Span(heading, style={"font-weight": "bold"}))
    children.append(
        dcc.Dropdown(
            id={"id": parent.uuid(id_string), "tab": tab},
            options=[{"label": ens, "value": ens} for ens in parent.pmodel.ensembles],
            multi=multi,
            value=value if value is not None else parent.pmodel.ensembles[0],
            clearable=False,
            persistence=True,
            persistence_type="session",
        )
    )
    return html.Div(style={"width": "90%"}, children=children)


def vector_selector(parent) -> html.Div:
    return html.Div(
        style={"width": "90%", "margin-top": "15px"},
        children=[
            html.Span("Vector type:", style={"font-weight": "bold"}),
            html.Div(
                id=parent.uuid("vtype-container"),
                children=[
                    dcc.RadioItems(
                        id={"id": parent.uuid("vtype-select"), "state": "initial"},
                        options=[
                            {"label": i, "value": i}
                            for i in parent.vmodel.vector_groups
                        ],
                        value="Field",
                        labelStyle={"display": "inline-block", "margin-right": "10px"},
                    )
                ],
            ),
            html.Div(
                style={"margin-top": "5px"},
                children=[
                    html.Span("Vector:", style={"font-weight": "bold"}),
                    html.Div(
                        id=parent.uuid("vshort-container"),
                        children=[
                            dcc.Dropdown(
                                id=parent.uuid("vshort-select"),
                                options=[
                                    {"label": i, "value": i}
                                    for i in parent.vmodel.vector_groups["Field"][
                                        "shortnames"
                                    ]
                                ],
                                value=parent.vmodel.vector_groups["Field"][
                                    "shortnames"
                                ][0],
                                placeholder="Select a vector...",
                                clearable=False,
                                persistence=True,
                                persistence_type="session",
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(id=parent.uuid("vitems-container"), children=[]),
            html.Div(id=parent.uuid("vector-select"), style={"display": "none"}),
            html.Div(id=parent.uuid("clickdata-store"), style={"display": "none"}),
        ],
    )


def parameter_selector(parent, tab: str) -> html.Div:
    return html.Div(
        style={"width": "90%", "margin-top": "15px"},
        children=[
            html.Span("Parameter:", style={"font-weight": "bold"}),
            dcc.Dropdown(
                id={"id": parent.uuid("parameter-select"), "tab": tab},
                options=[{"label": i, "value": i} for i in parent.pmodel.parameters],
                placeholder="Select a parameter...",
                clearable=False,
                persistence=True,
                persistence_type="session",
            ),
        ],
    )


def sortby_selector(
    parent,
    value: str = None,
) -> html.Div:
    return html.Div(
        style={"margin-top": "10px", "width": "90%"},
        children=[
            html.Span(
                "Sort parameters by:",
                style={"font-weight": "bold"},
            ),
            dcc.RadioItems(
                id=parent.uuid("delta-sort"),
                options=[
                    {"label": "Name", "value": "Name"},
                    {
                        "label": "StdDev",
                        "value": "Stddev",
                    },
                    {
                        "label": "Average",
                        "value": "Avg",
                    },
                ],
                value=value,
                labelStyle={
                    "display": "inline-block",
                    "margin-right": "5px",
                },
                persistence=True,
                persistence_type="session",
            ),
        ],
    )


def plot_options(parent, tab: str) -> html.Div:
    return html.Div(
        style={"width": "90%", "margin-top": "15px"},
        children=[
            dcc.Checklist(
                id={"id": parent.uuid("checkbox-options"), "tab": tab},
                options=[
                    {"label": "Dateline visible", "value": "DateLine"},
                    {"label": "Auto compute correlations", "value": "AutoCompute"},
                ],
                value=["DateLine", "AutoCompute"],
            ),
            html.Div(
                id={"id": parent.uuid("plot-options"), "tab": tab},
                style={"display": "none"},
            ),
        ],
    )


def date_selector(parent) -> html.Div:
    dates = parent.vmodel.dates
    return html.Div(
        style={"width": "90%", "margin-top": "15px"},
        children=[
            html.Div(
                style={"display": "inline-flex"},
                children=[
                    html.Span("Date:", style={"font-weight": "bold"}),
                    html.Span(
                        "date",
                        id=parent.uuid("date-selected"),
                        style={"margin-left": "10px"},
                    ),
                ],
            ),
            dcc.Slider(
                id=parent.uuid("date-slider"),
                value=len(dates) - 1,
                min=0,
                max=len(dates) - 1,
                included=False,
                marks={
                    idx: {
                        "label": dates[idx],
                        "style": {
                            "white-space": "nowrap",
                        },
                    }
                    for idx in [0, len(dates) - 1]
                },
            ),
        ],
    )


def filter_parameter(
    parent,
    tab: str,
    multi: bool = True,
    value: Union[str, float] = None,
) -> html.Div:
    return html.Div(
        style={"margin-top": "10px", "width": "90%"},
        children=[
            html.Span("Parameters:", style={"font-weight": "bold"}),
            html.Div(
                children=[
                    wcc.Select(
                        id={
                            "id": parent.uuid("filter-parameter"),
                            "tab": tab,
                        },
                        options=[
                            {"label": i, "value": i} for i in parent.pmodel.parameters
                        ],
                        value=value,
                        multi=multi,
                        size=min(40, len(parent.pmodel.parameters)),
                        persistence=True,
                        persistence_type="session",
                    ),
                ],
            ),
        ],
    )


def make_filter(
    parent,
    tab: str,
    vtype: str,
    column_values: list,
    multi: bool = True,
    value: Union[str, float] = None,
    open_details: bool = False,
) -> html.Div:
    return html.Div(
        children=html.Details(
            open=open_details,
            children=[
                html.Summary(vtype),
                wcc.Select(
                    id={
                        "id": parent.uuid("vitem-filter"),
                        "tab": tab,
                        "vtype": vtype,
                    },
                    options=[{"label": i, "value": i} for i in column_values],
                    value=[value] if value is not None else column_values,
                    multi=multi,
                    size=min(15, len(column_values)),
                    persistence=True,
                    persistence_type="session",
                ),
            ],
        ),
    )


def filter_vector_selector(
    parent,
    tab: str,
    multi: bool = True,
    value: Union[str, float] = None,
    open_details: bool = False,
) -> html.Div:
    return html.Div(
        style={"width": "90%"},
        children=[
            html.Span("Vector type:", style={"font-weight": "bold"}),
            dcc.Dropdown(
                id={
                    "id": parent.uuid("vtype-filter"),
                    "tab": tab,
                },
                options=[{"label": i, "value": i} for i in parent.vmodel.vector_groups],
                value=list(parent.vmodel.vector_groups),
                clearable=False,
                style={"background-color": "white"},
                multi=True,
                persistence=True,
                persistence_type="session",
            ),
            html.Div(
                children=[
                    make_filter(
                        parent=parent,
                        tab=tab,
                        vtype=f"{vtype}s",
                        column_values=vlist["items"],
                        multi=multi,
                        value=value,
                        open_details=open_details,
                    )
                    for vtype, vlist in parent.vmodel.vector_groups.items()
                    if vlist["items"]
                ],
            ),
            html.Div(
                id={"id": parent.uuid("filter-select"), "tab": tab},
                style={"display": "none"},
            ),
        ],
    )


def color_selector(parent, tab: str, px_colors: dict = None, height=None):
    custom_colors = {
        "theme": parent.theme.plotly_theme.get("layout", {}).get("colorway", {})[1:12]
    }

    return html.Div(
        style={"width": "90%", "margin-top": "5px"},
        children=[
            html.Span("Colors:", style={"font-weight": "bold"}),
            wcc.Graph(
                id={"id": parent.uuid("color-selector"), "tab": tab},
                config={"displayModeBar": False},
                figure=color_figure(
                    px_colors,
                    custom_colors=custom_colors,
                    height=height,
                ),
            ),
        ],
    )


def color_opacity_selector(parent, tab: str, value):
    return html.Div(
        style={"width": "90%", "margin-top": "5px"},
        children=[
            "Opacity:",
            dcc.Input(
                id={"id": parent.uuid("opacity-selector"), "tab": tab},
                type="number",
                min=0,
                max=1,
                step=0.1,
                value=value,
                style={"margin-left": "10px"},
            ),
        ],
    )


def html_details(
    summary: str,
    children: list,
    open_details: bool = False,
) -> html.Div:
    return html.Div(
        html.Details(
            style={"margin-bottom": "25px"},
            open=open_details,
            children=[
                html.Summary(
                    children=summary,
                    style={
                        "color": "#ff1243",
                        "border-bottom-style": "solid",
                        "border-width": "thin",
                        "border-color": "#ff1243",
                        "font-weight": "bold",
                        "font-size": "20px",
                        "margin-bottom": "15px",
                    },
                )
            ]
            + children,
        )
    )
