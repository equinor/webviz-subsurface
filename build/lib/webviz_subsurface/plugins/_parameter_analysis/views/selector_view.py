from typing import Callable, Optional, Union

import webviz_core_components as wcc
import webviz_subsurface_components as wsc
from dash import dcc, html

from .._utils import datetime_utils
from ..figures.color_figure import color_figure
from ..models import ParametersModel, SimulationTimeSeriesModel


def ensemble_selector(
    get_uuid: Callable,
    ensembles: list,
    tab: str,
    id_string: str,
    multi: bool = False,
    value: str = None,
    heading: str = None,
) -> html.Div:
    return wcc.Dropdown(
        label=heading,
        id={"id": get_uuid(id_string), "tab": tab},
        options=[{"label": ens, "value": ens} for ens in ensembles],
        multi=multi,
        value=value if value is not None else ensembles[0],
        clearable=False,
    )


def vector_selector(get_uuid: Callable, vectormodel: SimulationTimeSeriesModel):
    return wsc.VectorSelector(
        id=get_uuid("vector-selector"),
        maxNumSelectedNodes=1,
        data=vectormodel.vector_selector_data,
        persistence=True,
        persistence_type="session",
        selectedTags=["FOPT"]
        if "FOPT" in vectormodel.vectors
        else vectormodel.vectors[:1],
        numSecondsUntilSuggestionsAreShown=0.5,
        lineBreakAfterTag=True,
    )


def parameter_selector(
    get_uuid: Callable, parametermodel: ParametersModel, tab: str
) -> html.Div:
    return wcc.Dropdown(
        label="Parameter",
        id={"id": get_uuid("parameter-select"), "tab": tab},
        options=[{"label": i, "value": i} for i in parametermodel.parameters],
        placeholder="Select a parameter...",
        clearable=False,
    )


def sortby_selector(
    get_uuid: Callable,
    value: str = None,
) -> html.Div:
    return html.Div(
        wcc.RadioItems(
            label="Sort parameters by",
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
        )
    )


def plot_options(get_uuid: Callable, tab: str) -> html.Div:
    return html.Div(
        children=[
            wcc.Checklist(
                id={"id": get_uuid("checkbox-options"), "tab": tab},
                options=[
                    {"label": "Dateline visible", "value": "DateLine"},
                    {"label": "Auto compute correlations", "value": "AutoCompute"},
                ],
                value=["DateLine", "AutoCompute"],
            ),
            dcc.Store(
                id={"id": get_uuid("plot-options"), "tab": tab}, storage_type="session"
            ),
        ],
    )


def date_selector(
    get_uuid: Callable, vectormodel: SimulationTimeSeriesModel
) -> html.Div:
    dates = vectormodel.dates
    return html.Div(
        style={"margin": "10px 0px"},
        children=[
            html.Div(
                style={"display": "inline-flex"},
                children=[
                    wcc.Label("Date:"),
                    wcc.Label(
                        datetime_utils.to_str(dates[-1]),
                        id=get_uuid("date-selected-text"),
                        style={"margin-left": "10px"},
                    ),
                    dcc.Store(
                        id=get_uuid("date-selected"),
                        storage_type="session",
                        data=datetime_utils.to_str(dates[-1]),
                    ),
                ],
            ),
            wcc.Slider(
                id=get_uuid("date-slider"),
                value=len(dates) - 1,
                min=0,
                max=len(dates) - 1,
                step=1,
                included=False,
                marks={
                    idx: {
                        "label": datetime_utils.to_str(dates[idx]),
                        "style": {"white-space": "nowrap"},
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
        style={"margin-top": "10px"},
        children=[
            wcc.Label("Select parameters"),
            html.Div(
                id=get_uuid("filter-parameter-container"),
                children=[
                    wcc.SelectWithLabel(
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
) -> wcc.Selectors:
    return html.Details(
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
            ),
        ],
    )


def button(uuid, label, height="30px"):
    return html.Button(
        label,
        id=uuid,
        style={
            "marginBottom": "5px",
            "width": "100%",
            "height": height,
            "line-height": height,
            "background-color": "#E8E8E8",
        },
    )


def filter_vector_selector(get_uuid: Callable) -> html.Div:
    return html.Div(
        children=[
            dcc.Textarea(
                id=get_uuid("vector-filter"),
                style={"width": "95%", "height": "60px", "resize": "none"},
                placeholder="\nenter comma separated input\n* is used as wildcard",
                persistence=True,
                persistence_type="session",
            ),
            button(get_uuid("submit-vector-filter"), "Submit", height="20px"),
            dcc.Store(id=get_uuid("vector-filter-store")),
        ]
    )


def color_selector(
    get_uuid: Callable,
    tab: str,
    colors: Optional[list] = None,
    bargap: Optional[float] = None,
    height: Optional[float] = None,
):
    return html.Div(
        style={"margin-top": "5px"},
        children=[
            wcc.Label("Colors"),
            wcc.Graph(
                style={"height": height},
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
        style={"margin-top": "5px"},
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
