import datetime
from typing import Callable, List, Any
from enum import Enum
import webviz_core_components as wcc
import webviz_subsurface_components as wsc
from dash import html, dcc, dash_table

from ._utils import datetime_utils

from ._business_logic import SimulationTimeSeriesOneByOneDataModel

# pylint: disable = too-few-public-methods
class LayoutElements(str, Enum):
    PLOT_WRAPPER = "plot-wrapper"
    PLOT_SELECTOR = "plot-wrapper"


class LayoutStyle:
    MAIN_HEIGHT = "87vh"


class FullScreen(wcc.WebvizPluginPlaceholder):
    def __init__(self, children: List[Any]) -> None:
        super().__init__(buttons=["expand"], children=children)


def main_view(
    get_uuid: Callable, datamodel: SimulationTimeSeriesOneByOneDataModel
) -> wcc.FlexBox:
    return wcc.FlexBox(
        id=get_uuid("layout"),
        children=[
            wcc.FlexColumn(
                flex=1,
                children=selector_view(get_uuid, datamodel),
            ),
            wcc.FlexColumn(flex=6, children=data_view(get_uuid, datamodel)),
        ],
    )


def selector_view(
    get_uuid: Callable, datamodel: SimulationTimeSeriesOneByOneDataModel
) -> html.Div:
    initial_date = datamodel.vmodel.get_last_date(datamodel.ensembles[0])
    return wcc.Frame(
        style={"height": "90vh"},
        children=[
            wcc.Selectors(
                label="Selectors",
                children=[
                    ensemble_selector(get_uuid, datamodel.ensembles),
                    vector_selector(
                        get_uuid,
                        datamodel.vmodel.vector_selector_data,
                        datamodel.initial_vector,
                    ),
                    html.Div(
                        id=get_uuid("date_selector_wrapper"),
                        children=date_selector(
                            get_uuid,
                            date_selected=initial_date,
                            dates=datamodel.vmodel.dates_for_ensemble(
                                datamodel.ensembles[0]
                            ),
                        ),
                    ),
                ],
            ),
            wcc.Selectors(
                label="Visualization",
                children=visualization_selector(get_uuid),
            ),
            wcc.Selectors(
                label="Sensitivity filter",
                children=sensitivity_selector(get_uuid, datamodel.pmodel.sensitivities),
            ),
            wcc.Selectors(
                label="⚙️ SETTINGS",
                open_details=True,
                children=[
                    scale_selector(get_uuid),
                    checkboxes_settings(get_uuid),
                    labels_display(get_uuid),
                    reference_selector(get_uuid, datamodel.pmodel.sensitivities),
                    dcc.Store(get_uuid("options-store")),
                    dcc.Store(get_uuid("real-store")),
                    dcc.Store(
                        get_uuid("date-store"), data=datetime_utils.to_str(initial_date)
                    ),
                    dcc.Store(get_uuid("vector-store")),
                ],
            ),
        ],
    )


def data_view(
    get_uuid: Callable, datamodel: SimulationTimeSeriesOneByOneDataModel
) -> wcc.FlexBox:
    initial_date = datetime_utils.to_str(
        datamodel.vmodel.get_last_date(datamodel.ensembles[0])
    )

    return html.Div(
        children=[
            wcc.FlexBox(
                children=[
                    wcc.FlexColumn(
                        children=wcc.Frame(
                            style={"height": "50vh"},
                            color="white",
                            highlight=False,
                            children=wcc.Graph(
                                id=get_uuid("graph"),
                                style={"height": "48vh"},
                                clickData={"points": [{"x": initial_date}]},
                            ),
                        ),
                    ),
                    wcc.FlexColumn(
                        children=wcc.Frame(
                            style={"height": "50vh"},
                            color="white",
                            highlight=False,
                            id=get_uuid("tornado-wrapper"),
                            children=FullScreen(
                                wcc.Graph(
                                    config={"displayModeBar": False},
                                    style={"height": "100%", "min-height": "46vh"},
                                    id=get_uuid("tornado-graph"),
                                ),
                            ),
                        ),
                    ),
                ]
            ),
            wcc.Frame(
                style={"height": "37vh"},
                color="white",
                highlight=False,
                children=[
                    html.Div(
                        id=get_uuid("table-wrapper"),
                        style={"display": "block"},
                        children=dash_table.DataTable(
                            id=get_uuid("table"),
                            sort_action="native",
                            sort_mode="multi",
                            filter_action="native",
                            style_as_list_view=True,
                            style_table={"height": "35vh", "overflowY": "auto"},
                        ),
                    ),
                    html.Div(
                        id=get_uuid("real-graph-wrapper"),
                        style={"display": "none"},
                        children=wcc.Graph(
                            config={"displayModeBar": False},
                            style={"height": "35vh"},
                            id=get_uuid("real-graph"),
                        ),
                    ),
                ],
            ),
        ]
    )


def checkboxes_settings(get_uuid: Callable) -> html.Div:
    return html.Div(
        style={"margin-top": "10px", "margin-bottom": "10px"},
        children=[
            wcc.Checklist(
                id={"id": get_uuid("options"), "selector": selector},
                options=[{"label": label, "value": "selected"}],
                value=["selected"] if selected else [],
            )
            for label, selector, selected in [
                ("Color by sensitivity", "color_by_sens", True),
                ("Show realization points", "real_scatter", False),
                ("Show reference on tornado", "torn_ref", True),
                ("Remove sensitivities with no impact", "Remove no impact", True),
            ]
        ],
    )


def labels_display(get_uuid: Callable) -> html.Div:
    return html.Div(
        style={"margin-bottom": "10px"},
        children=[
            wcc.RadioItems(
                label="Label options:",
                id={"id": get_uuid("options"), "selector": "labeloptions"},
                options=[
                    {"label": "detailed", "value": "detailed"},
                    {"label": "simple", "value": "simple"},
                    {"label": "hide", "value": "hide"},
                ],
                vertical=False,
                value="simple",
            ),
        ],
    )


def reference_selector(get_uuid: Callable, sensitivities: list) -> wcc.Dropdown:
    return wcc.Dropdown(
        label="Reference:",
        id={"id": get_uuid("options"), "selector": "Reference"},
        options=[{"label": elm, "value": elm} for elm in sensitivities],
        value="rms_seed" if "rms_seed" in sensitivities else sensitivities[0],
        clearable=False,
    )


def date_selector(
    get_uuid: Callable, date_selected: datetime.datetime, dates: List[datetime.datetime]
) -> html.Div:
    return html.Div(
        style={"margin": "10px 0px"},
        children=[
            html.Div(
                style={"display": "inline-flex"},
                children=[
                    wcc.Label("Date:"),
                    wcc.Label(
                        datetime_utils.to_str(date_selected),
                        id={"id": get_uuid("date-selected-text"), "test": "test"},
                        style={"margin-left": "10px"},
                    ),
                ],
            ),
            wcc.Slider(
                id={"id": get_uuid("date-slider"), "test": "test"},
                value=dates.index(date_selected),
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


def scale_selector(get_uuid: Callable) -> wcc.Dropdown:
    return wcc.Dropdown(
        label="Scale:",
        id={"id": get_uuid("options"), "selector": "Scale"},
        options=[
            {"label": "Relative value (%)", "value": "Percentage"},
            {"label": "Relative value", "value": "Absolute"},
            {"label": "True value", "value": "True"},
        ],
        value="Percentage",
        clearable=False,
    )


def ensemble_selector(get_uuid: Callable, ensembles: list) -> html.Div:
    """Dropdown to select ensemble"""
    return wcc.Dropdown(
        label="Ensemble",
        id=get_uuid("ensemble"),
        options=[{"label": i, "value": i} for i in ensembles],
        clearable=False,
        value=ensembles[0],
    )


def visualization_selector(get_uuid: Callable) -> html.Div:
    """Dropdown to select ensemble"""
    return html.Div(
        [
            wcc.RadioItems(
                id=get_uuid("visualization"),
                options=[
                    {"label": "Individual realizations", "value": "realizations"},
                    {"label": "Mean over Sensitivities", "value": "sensmean"},
                ],
                value="realizations",
            ),
            html.Div(
                style={"margin-top": "10px"},
                children=wcc.RadioItems(
                    label="Bottom visualization:",
                    id=get_uuid("bottom-viz"),
                    options=[
                        {"label": "Table", "value": "table"},
                        {"label": "Realization plot", "value": "realplot"},
                    ],
                    vertical=False,
                    value="table",
                ),
            ),
        ]
    )


def sensitivity_selector(get_uuid: Callable, sensitivities: list) -> html.Div:
    """Dropdown to select ensemble"""
    return wcc.SelectWithLabel(
        id=get_uuid("sensitivity_filter"),
        options=[{"label": i, "value": i} for i in sensitivities],
        value=sensitivities,
        size=min(20, len(sensitivities)),
    )


def vector_selector(
    get_uuid: Callable, vector_selector_data: list, initial_vector: str
) -> html.Div:
    """Dropdown to select ensemble"""
    return wsc.VectorSelector(
        id=get_uuid("vector"),
        maxNumSelectedNodes=1,
        data=vector_selector_data,
        persistence=True,
        persistence_type="session",
        selectedTags=[initial_vector],
        numSecondsUntilSuggestionsAreShown=0.5,
        lineBreakAfterTag=True,
    )
