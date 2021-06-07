from typing import Union, Optional, Callable

import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc

from ..figures.color_figure import color_figure
from ..models import ParametersModel, SimulationTimeSeriesModel


def ensemble_selector(
    get_uuid: Callable,
    parametermodel: ParametersModel,
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
            id={"id": get_uuid(id_string), "tab": tab},
            options=[{"label": ens, "value": ens} for ens in parametermodel.ensembles],
            multi=multi,
            value=value if value is not None else parametermodel.ensembles[0],
            clearable=False,
            persistence=True,
            persistence_type="session",
        )
    )
    return html.Div(style={"width": "90%"}, children=children)


def vector_selector(
    get_uuid: Callable, vectormodel: SimulationTimeSeriesModel
) -> html.Div:
    first_vector_group: str = (
        "Field"
        if "Field" in list(vectormodel.vector_groups.keys())
        else list(vectormodel.vector_groups.keys())[0]
    )
    return html.Div(
        style={"width": "90%", "margin-top": "15px"},
        children=[
            html.Span("Vector type:", style={"font-weight": "bold"}),
            html.Div(
                id=get_uuid("vtype-container"),
                children=[
                    dcc.RadioItems(
                        id={"id": get_uuid("vtype-select"), "state": "initial"},
                        options=[
                            {"label": i, "value": i} for i in vectormodel.vector_groups
                        ],
                        value=first_vector_group,
                        labelStyle={"display": "inline-block", "margin-right": "10px"},
                    )
                ],
            ),
            html.Div(
                style={"margin-top": "5px"},
                children=[
                    html.Span("Vector:", style={"font-weight": "bold"}),
                    html.Div(
                        id=get_uuid("vshort-container"),
                        children=[
                            dcc.Dropdown(
                                id=get_uuid("vshort-select"),
                                options=[
                                    {"label": i, "value": i}
                                    for i in vectormodel.vector_groups[
                                        first_vector_group
                                    ]["shortnames"]
                                ],
                                value=vectormodel.vector_groups[first_vector_group][
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
            html.Div(id=get_uuid("vitems-container"), children=[]),
            html.Div(id=get_uuid("vector-select"), style={"display": "none"}),
            html.Div(id=get_uuid("clickdata-store"), style={"display": "none"}),
        ],
    )


def parameter_selector(
    get_uuid: Callable, parametermodel: ParametersModel, tab: str
) -> html.Div:
    return html.Div(
        style={"width": "90%", "margin-top": "15px"},
        children=[
            html.Span("Parameter:", style={"font-weight": "bold"}),
            dcc.Dropdown(
                id={"id": get_uuid("parameter-select"), "tab": tab},
                options=[{"label": i, "value": i} for i in parametermodel.parameters],
                placeholder="Select a parameter...",
                clearable=False,
                persistence=True,
                persistence_type="session",
            ),
        ],
    )


def sortby_selector(
    get_uuid: Callable,
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
                id=get_uuid("delta-sort"),
                className="block-options",
                options=[
                    {"label": "Name", "value": "Name"},
                    {
                        "label": "Standard deviation",
                        "value": "Stddev",
                    },
                    {
                        "label": "Average",
                        "value": "Avg",
                    },
                ],
                value=value,
                persistence=True,
                persistence_type="session",
            ),
        ],
    )


def plot_options(get_uuid: Callable, tab: str) -> html.Div:
    return html.Div(
        style={"width": "90%", "margin-top": "15px"},
        children=[
            dcc.Checklist(
                id={"id": get_uuid("checkbox-options"), "tab": tab},
                className="block-options",
                options=[
                    {"label": "Dateline visible", "value": "DateLine"},
                    {"label": "Auto compute correlations", "value": "AutoCompute"},
                ],
                value=["DateLine", "AutoCompute"],
            ),
            html.Div(
                id={"id": get_uuid("plot-options"), "tab": tab},
                style={"display": "none"},
            ),
        ],
    )


def date_selector(
    get_uuid: Callable, vectormodel: SimulationTimeSeriesModel
) -> html.Div:
    dates = vectormodel.dates
    return html.Div(
        style={"width": "90%", "margin-top": "15px"},
        children=[
            html.Div(
                style={"display": "inline-flex"},
                children=[
                    html.Span("Date:", style={"font-weight": "bold"}),
                    html.Span(
                        "date",
                        id=get_uuid("date-selected"),
                        style={"margin-left": "10px"},
                    ),
                ],
            ),
            dcc.Slider(
                id=get_uuid("date-slider"),
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
    get_uuid: Callable,
    parametermodel: ParametersModel,
    tab: str,
    multi: bool = True,
    value: Union[str, float] = None,
) -> html.Div:
    return html.Div(
        style={"margin-top": "10px", "width": "90%"},
        children=[
            html.Span("Parameters:", style={"font-weight": "bold"}),
            html.Div(
                id=get_uuid("filter-parameter-container"),
                children=[
                    wcc.Select(
                        id={
                            "id": get_uuid("filter-parameter"),
                            "tab": tab,
                        },
                        options=[
                            {"label": i, "value": i} for i in parametermodel.parameters
                        ],
                        value=value,
                        multi=multi,
                        size=min(40, len(parametermodel.parameters)),
                        persistence=True,
                        persistence_type="session",
                    ),
                ],
            ),
        ],
    )


def make_filter(
    get_uuid: Callable,
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
                        "id": get_uuid("vitem-filter"),
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
    get_uuid: Callable,
    vectormodel: SimulationTimeSeriesModel,
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
                    "id": get_uuid("vtype-filter"),
                    "tab": tab,
                },
                options=[{"label": i, "value": i} for i in vectormodel.vector_groups],
                value=list(vectormodel.vector_groups),
                clearable=False,
                style={"background-color": "white"},
                multi=True,
                persistence=True,
                persistence_type="session",
            ),
            html.Div(
                children=[
                    make_filter(
                        get_uuid=get_uuid,
                        tab=tab,
                        vtype=f"{vtype}s",
                        column_values=vlist["items"],
                        multi=multi,
                        value=value,
                        open_details=open_details,
                    )
                    for vtype, vlist in vectormodel.vector_groups.items()
                    if vlist["items"]
                ],
            ),
            html.Div(
                id={"id": get_uuid("filter-select"), "tab": tab},
                style={"display": "none"},
            ),
        ],
    )


def color_selector(
    get_uuid: Callable,
    tab: str,
    colors: Optional[list] = None,
    bargap: Optional[float] = None,
    height: Optional[float] = None,
):
    return html.Div(
        style={"width": "90%", "margin-top": "5px"},
        children=[
            html.Span("Colors:", style={"font-weight": "bold"}),
            wcc.Graph(
                id={"id": get_uuid("color-selector"), "tab": tab},
                config={"displayModeBar": False},
                figure=color_figure(
                    colors=colors,
                    bargap=bargap,
                    height=height,
                ),
            ),
        ],
    )


def color_opacity_selector(get_uuid: Callable, tab: str, value: float):
    return html.Div(
        style={"width": "90%", "margin-top": "5px"},
        children=[
            "Opacity:",
            dcc.Input(
                id={"id": get_uuid("opacity-selector"), "tab": tab},
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
