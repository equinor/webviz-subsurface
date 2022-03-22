from typing import Callable, List, Union

import webviz_core_components as wcc
import webviz_subsurface_components as wsc
from dash import html

from ..models import (
    PropertyStatisticsModel,
    ProviderTimeSeriesDataModel,
    SimulationTimeSeriesModel,
)


def vector_selector(
    get_uuid: Callable,
    vector_model: Union[SimulationTimeSeriesModel, ProviderTimeSeriesDataModel],
) -> wsc.VectorSelector:
    return wsc.VectorSelector(
        id=get_uuid("property-response-vector-select"),
        maxNumSelectedNodes=1,
        data=vector_model.vector_selector_data,
        persistence=True,
        persistence_type="session",
        selectedTags=vector_model.vectors[:1],
        numSecondsUntilSuggestionsAreShown=0.5,
        lineBreakAfterTag=True,
    )


def ensemble_selector(
    get_uuid: Callable,
    ensembles: List[str],
    tab: str,
    multi: bool = False,
    initial_ensemble: str = None,
) -> html.Div:
    return wcc.Dropdown(
        label="Ensemble",
        id={"id": get_uuid("ensemble-selector"), "tab": tab},
        options=[{"label": ens, "value": ens} for ens in ensembles],
        multi=multi,
        value=initial_ensemble if initial_ensemble is not None else ensembles[0],
        clearable=False,
    )


def delta_ensemble_selector(
    get_uuid: Callable, ensembles: List[str], tab: str, multi: bool = False
) -> html.Div:
    return wcc.Dropdown(
        label="Delta Ensemble",
        id={"id": get_uuid("delta-ensemble-selector"), "tab": tab},
        options=[{"label": ens, "value": ens} for ens in ensembles],
        multi=multi,
        value=ensembles[-1],
        clearable=False,
    )


def property_selector(
    get_uuid: Callable,
    properties: List[str],
    tab: str,
    multi: bool = False,
    initial_property: str = None,
) -> html.Div:
    display = "none" if len(properties) < 2 else "inline"
    return html.Div(
        style={"display": display},
        children=[
            wcc.Dropdown(
                label="Property",
                id={"id": get_uuid("property-selector"), "tab": tab},
                options=[{"label": prop, "value": prop} for prop in properties],
                multi=multi,
                value=initial_property
                if initial_property is not None
                else properties[0],
                clearable=False,
            )
        ],
    )


def source_selector(
    get_uuid: Callable,
    sources: List[str],
    tab: str,
    multi: bool = False,
    initial_source: str = None,
) -> html.Div:
    display = "none" if len(sources) < 2 else "inline"
    return html.Div(
        style={"display": display},
        children=[
            wcc.Dropdown(
                label="Source",
                id={"id": get_uuid("source-selector"), "tab": tab},
                options=[{"label": source, "value": source} for source in sources],
                multi=multi,
                value=initial_source if initial_source is not None else sources[0],
                clearable=False,
            ),
        ],
    )


def make_filter(
    get_uuid: Callable,
    tab: str,
    df_column: str,
    column_values: list,
    multi: bool = True,
    value: Union[str, float] = None,
) -> html.Div:
    return wcc.SelectWithLabel(
        label=df_column.lower().capitalize(),
        id={
            "id": get_uuid("filter-selector"),
            "tab": tab,
            "selector": df_column,
        },
        options=[{"label": i, "value": i} for i in column_values],
        value=[value] if value is not None else column_values,
        multi=multi,
        size=min(20, len(column_values)),
    )


def filter_selector(
    get_uuid: Callable,
    property_model: PropertyStatisticsModel,
    tab: str,
    multi: bool = True,
    value: Union[str, float] = None,
) -> html.Div:
    return html.Div(
        children=[
            html.Div(
                children=[
                    make_filter(
                        get_uuid=get_uuid,
                        tab=tab,
                        df_column=sel,
                        column_values=property_model.selector_values(sel),
                        multi=multi,
                        value=value,
                    )
                    for sel in property_model.selectors
                ]
            ),
        ]
    )
