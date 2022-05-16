import datetime
from typing import Callable, Dict, List, Set

import webviz_core_components as wcc
from dash import html

from .._ensemble_well_analysis_data import EnsembleWellAnalysisData
from .._types import ChartType


# pylint: disable = too-few-public-methods
class WellOverviewLayoutElements:
    GRAPH_FRAME = "well-overview-graph-frame"
    GRAPH = "well-overview-graph"
    ENSEMBLES = "well-overview-ensembles"
    SUMVEC = "well-overview-sumvec"
    CHARTTYPE_BUTTON = "well-overview-charttype-button"
    CHARTTYPE_SETTINGS = "well-overview-charttype-settings"
    CHARTTYPE_CHECKLIST = "well-overview-charttype-checklist"
    WELL_FILTER = "well-overview-well-filter"
    WELL_ATTRIBUTES = "well-overview-well-attributes"
    DATE = "well-overview-date"


def well_overview_tab(
    get_uuid: Callable, data_models: Dict[str, EnsembleWellAnalysisData]
) -> wcc.FlexBox:
    """Well overview tab"""
    return wcc.FlexBox(
        children=[
            wcc.Frame(
                style={"flex": 1, "height": "87vh"},
                children=[
                    buttons(get_uuid),
                    controls(get_uuid, data_models),
                    filters(get_uuid, data_models),
                    plot_settings(get_uuid),
                ],
            ),
            wcc.Frame(
                style={"flex": 4, "height": "87vh"},
                color="white",
                highlight=False,
                id=get_uuid(WellOverviewLayoutElements.GRAPH_FRAME),
                children=[
                    wcc.Graph(
                        id=get_uuid(WellOverviewLayoutElements.GRAPH),
                    )
                ],
            ),
        ]
    )


def buttons(get_uuid: Callable) -> html.Div:
    uuid = get_uuid(WellOverviewLayoutElements.CHARTTYPE_BUTTON)
    return html.Div(
        style={"margin-bottom": "20px"},
        children=[
            html.Button(
                "Bar Chart",
                className="webviz-inplace-vol-btn",
                id={"id": uuid, "button": ChartType.BAR},
            ),
            html.Button(
                "Pie Chart",
                className="webviz-inplace-vol-btn",
                id={"id": uuid, "button": ChartType.PIE},
            ),
            html.Button(
                "Stacked Area Chart",
                className="webviz-inplace-vol-btn",
                id={"id": uuid, "button": ChartType.AREA},
            ),
        ],
    )


def controls(
    get_uuid: Callable, data_models: Dict[str, EnsembleWellAnalysisData]
) -> wcc.Selectors:
    ensembles = list(data_models.keys())
    dates: Set[datetime.datetime] = set()
    for _, ens_data_model in data_models.items():
        dates = dates.union(ens_data_model.dates)
    sorted_dates: List[datetime.datetime] = sorted(list(dates))

    return wcc.Selectors(
        label="Plot Controls",
        children=[
            wcc.Dropdown(
                label="Ensembles",
                id=get_uuid(WellOverviewLayoutElements.ENSEMBLES),
                options=[{"label": col, "value": col} for col in ensembles],
                value=ensembles,
                multi=True,
            ),
            wcc.Dropdown(
                label="Response",
                id=get_uuid(WellOverviewLayoutElements.SUMVEC),
                options=[
                    {"label": "Oil production", "value": "WOPT"},
                    {"label": "Gas production", "value": "WGPT"},
                    {"label": "Water production", "value": "WWPT"},
                ],
                value="WOPT",
                multi=False,
                clearable=False,
            ),
            wcc.Dropdown(
                label="Only Production after date",
                id=get_uuid(WellOverviewLayoutElements.DATE),
                options=[
                    {
                        "label": dte.strftime("%Y-%m-%d"),
                        "value": dte.strftime("%Y-%m-%d"),
                    }
                    for dte in sorted_dates
                ],
                multi=False,
            ),
        ],
    )


def filters(
    get_uuid: Callable, data_models: Dict[str, EnsembleWellAnalysisData]
) -> wcc.Selectors:
    # Collecting wells and well_attributes from all ensembles.
    wells = []
    well_attr = {}
    for _, ens_data_model in data_models.items():
        wells.extend([well for well in ens_data_model.wells if well not in wells])
        for category, values in ens_data_model.well_attributes.items():
            if category not in well_attr:
                well_attr[category] = values
            else:
                well_attr[category].extend(
                    [value for value in values if value not in well_attr[category]]
                )

    return wcc.Selectors(
        label="Filters",
        children=[
            wcc.SelectWithLabel(
                label="Well",
                size=min(10, len(wells)),
                id=get_uuid(WellOverviewLayoutElements.WELL_FILTER),
                options=[{"label": well, "value": well} for well in wells],
                value=wells,
                multi=True,
            )
        ]
        # Adding well attributes selectors
        + [
            wcc.SelectWithLabel(
                label=category.capitalize(),
                size=min(5, len(values)),
                id={
                    "id": get_uuid(WellOverviewLayoutElements.WELL_ATTRIBUTES),
                    "category": category,
                },
                options=[{"label": value, "value": value} for value in values],
                value=values,
                multi=True,
            )
            for category, values in well_attr.items()
        ],
    )


def plot_settings(get_uuid: Callable) -> wcc.Frame:
    settings_uuid = get_uuid(WellOverviewLayoutElements.CHARTTYPE_SETTINGS)
    checklist_uuid = get_uuid(WellOverviewLayoutElements.CHARTTYPE_CHECKLIST)
    return wcc.Selectors(
        label="Plot Settings",
        children=[
            html.Div(
                id={"id": settings_uuid, "charttype": "bar"},
                children=wcc.Checklist(
                    id={"id": checklist_uuid, "charttype": "bar"},
                    options=[
                        {"label": "Show legend", "value": "legend"},
                        {"label": "Overlay bars", "value": "overlay_bars"},
                        {"label": "Show prod as text", "value": "show_prod_text"},
                        {"label": "White background", "value": "white_background"},
                    ],
                    value=["legend"],
                ),
            ),
            html.Div(
                id={"id": settings_uuid, "charttype": "pie"},
                children=wcc.Checklist(
                    id={"id": checklist_uuid, "charttype": "pie"},
                    options=[
                        {"label": "Show legend", "value": "legend"},
                        {"label": "Show prod as text", "value": "show_prod_text"},
                    ],
                    value=[],
                ),
            ),
            html.Div(
                id={"id": settings_uuid, "charttype": "area"},
                children=wcc.Checklist(
                    id={"id": checklist_uuid, "charttype": "area"},
                    options=[
                        {"label": "Show legend", "value": "legend"},
                        {"label": "White background", "value": "white_background"},
                    ],
                    value=["legend"],
                ),
            ),
        ],
    )
