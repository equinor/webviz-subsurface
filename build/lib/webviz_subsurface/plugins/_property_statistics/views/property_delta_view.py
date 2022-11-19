from typing import Any, Callable, Dict, List, Optional

import webviz_core_components as wcc
import webviz_subsurface_components as wsc
from dash import dash_table, html

from ..models import PropertyStatisticsModel
from .selector_view import (
    delta_ensemble_selector,
    ensemble_selector,
    filter_selector,
    property_selector,
    source_selector,
)


def surface_select_view(get_uuid: Callable, tab: str) -> html.Div:
    return html.Div(
        id=get_uuid("surface-select"),
        style={"width": "75%"},
        children=wcc.Dropdown(
            label="Surface statistics",
            id={"id": get_uuid("surface-type"), "tab": tab},
            options=[
                {"label": "Mean", "value": "mean"},
                {"label": "Standard Deviation", "value": "stddev"},
                {"label": "Minimum", "value": "min"},
                {"label": "Maximum", "value": "max"},
                {"label": "P10", "value": "p10"},
                {"label": "P90", "value": "p90"},
            ],
            clearable=False,
            value="mean",
        ),
    )


def surface_view(
    get_uuid: Callable, ensemble: str, layers: list, synced_ids: list = None
) -> wsc.LeafletMap:
    return html.Div(
        style={"height": "22vh"},
        children=wsc.LeafletMap(
            id=f"{get_uuid('surface-view-delta')}{ensemble}",
            layers=layers,
            syncedMaps=[
                f"{get_uuid('surface-view-delta')}{s_id}" for s_id in synced_ids
            ]
            if synced_ids is not None
            else [],
            unitScale={},
            autoScaleMap=True,
            minZoom=-19,
            updateMode="replace",
            mouseCoords={"position": "bottomright"},
            colorBar={"position": "bottomleft"},
        ),
    )


# pylint: disable=too-many-arguments
def surface_views(
    get_uuid: Callable,
    ensemble: str,
    delta_ensemble: str,
    ens_layer: dict,
    delta_ens_layer: dict,
    diff_layer: dict,
    prop: str,
    zone: str,
    statistic: str = "Mean",
) -> html.Div:
    return html.Div(
        style={"height": "76vh"},
        children=[
            wcc.Label(
                children=f"{statistic} for {prop}, {zone} in {ensemble}",
            ),
            surface_view(
                get_uuid=get_uuid,
                ensemble=ensemble,
                synced_ids=[delta_ensemble, "diff"],
                layers=[ens_layer],
            ),
            wcc.Label(
                children=f"{statistic} for {prop}, {zone} in {delta_ensemble}",
            ),
            surface_view(
                get_uuid=get_uuid,
                ensemble=delta_ensemble,
                synced_ids=[ensemble, "diff"],
                layers=[delta_ens_layer],
            ),
            wcc.Label(
                children=f"{statistic} for {prop}, {zone} in {ensemble} - {delta_ensemble}",
            ),
            surface_view(
                get_uuid=get_uuid,
                ensemble="diff",
                synced_ids=[delta_ensemble, ensemble],
                layers=[diff_layer],
            ),
        ],
    )


def selector_view(
    get_uuid: Callable, property_model: PropertyStatisticsModel
) -> html.Div:
    return wcc.Frame(
        style={"height": "80vh", "overflowY": "auto"},
        children=[
            wcc.Selectors(
                label="Selectors",
                children=[
                    ensemble_selector(
                        get_uuid=get_uuid,
                        ensembles=property_model.ensembles,
                        tab="delta",
                    ),
                    delta_ensemble_selector(
                        get_uuid=get_uuid,
                        ensembles=property_model.ensembles,
                        tab="delta",
                    ),
                    property_selector(
                        get_uuid=get_uuid,
                        properties=property_model.properties,
                        tab="delta",
                    ),
                    source_selector(
                        get_uuid=get_uuid, sources=property_model.sources, tab="delta"
                    ),
                ],
            ),
            wcc.Selectors(
                label="Filters",
                children=[
                    filter_selector(
                        get_uuid=get_uuid, property_model=property_model, tab="delta"
                    )
                ],
            ),
        ],
    )


def delta_avg_view() -> html.Div:
    return wcc.FlexColumn(
        children=[],
    )


def property_delta_view(
    get_uuid: Callable,
    property_model: PropertyStatisticsModel,
    surface_folders: Optional[Dict] = None,
) -> wcc.FlexBox:
    table_surf_options = [{"label": "Table view", "value": "table"}]
    if surface_folders is not None:
        table_surf_options.append(
            {"label": "Surface view (click on bar in chart)", "value": "surface"}
        )
    return wcc.FlexBox(
        style={"margin": "20px"},
        children=[
            wcc.FlexColumn(
                children=selector_view(get_uuid=get_uuid, property_model=property_model)
            ),
            wcc.FlexColumn(
                flex=4,
                children=wcc.Frame(
                    color="white",
                    highlight=False,
                    style={"height": "80vh"},
                    children=[
                        wcc.RadioItems(
                            vertical=False,
                            id=get_uuid("delta-sort"),
                            options=[
                                {"label": "Sort by Average", "value": "Avg"},
                                {
                                    "label": "Sort by Standard Deviation",
                                    "value": "Stddev",
                                },
                            ],
                            value="Avg",
                        ),
                        wcc.Graph(
                            id=get_uuid("delta-bar-graph"),
                            config={"displayModeBar": False},
                            style={"height": "75vh"},
                        ),
                    ],
                ),
            ),
            wcc.FlexColumn(
                flex=4,
                children=wcc.Frame(
                    style={"height": "80vh"},
                    color="white",
                    highlight=False,
                    children=[
                        wcc.RadioItems(
                            id=get_uuid("delta-switch-table-surface"),
                            vertical=False,
                            options=table_surf_options,
                            value="table",
                        ),
                        html.Div(id=get_uuid("delta-table-surface-wrapper")),
                    ],
                ),
            ),
        ],
    )


def table_view(data: List[Any], columns: List[Any]) -> html.Div:
    return dash_table.DataTable(
        sort_action="native",
        page_action="native",
        filter_action="native",
        style_table={"height": "74vh", "overflow": "auto", "fontSize": 13},
        data=data,
        columns=columns,
        style_cell={"textAlign": "center"},
        style_cell_conditional=[{"if": {"column_id": "label|"}, "textAlign": "left"}],
        merge_duplicate_headers=True,
    )
