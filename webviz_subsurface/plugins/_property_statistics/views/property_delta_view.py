from typing import List, Any, TYPE_CHECKING

import dash_html_components as html
import dash_table
import webviz_core_components as wcc
import webviz_subsurface_components as wsc

from .selector_view import (
    ensemble_selector,
    delta_ensemble_selector,
    property_selector,
    filter_selector,
    source_selector,
)

if TYPE_CHECKING:
    # pylint: disable=cyclic-import
    from ..property_statistics import PropertyStatistics


def surface_select_view(parent: "PropertyStatistics", tab: str) -> html.Div:
    return html.Div(
        id=parent.uuid("surface-select"),
        style={"width": "75%"},
        children=wcc.Dropdown(
            label="Surface statistics",
            id={"id": parent.uuid("surface-type"), "tab": tab},
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
    parent: "PropertyStatistics", ensemble: str, layers: list, synced_ids: list = None
) -> wsc.LeafletMap:
    return html.Div(
        style={"height": "22vh"},
        children=wsc.LeafletMap(
            id=f"{parent.uuid('surface-view-delta')}{ensemble}",
            layers=layers,
            syncedMaps=[
                f"{parent.uuid('surface-view-delta')}{s_id}" for s_id in synced_ids
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
    parent: "PropertyStatistics",
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
                parent=parent,
                ensemble=ensemble,
                synced_ids=[delta_ensemble, "diff"],
                layers=[ens_layer],
            ),
            wcc.Label(
                children=f"{statistic} for {prop}, {zone} in {delta_ensemble}",
            ),
            surface_view(
                parent=parent,
                ensemble=delta_ensemble,
                synced_ids=[ensemble, "diff"],
                layers=[delta_ens_layer],
            ),
            wcc.Label(
                children=f"{statistic} for {prop}, {zone} in {ensemble} - {delta_ensemble}",
            ),
            surface_view(
                parent=parent,
                ensemble="diff",
                synced_ids=[delta_ensemble, ensemble],
                layers=[diff_layer],
            ),
        ],
    )


def selector_view(parent: "PropertyStatistics") -> html.Div:
    return wcc.Frame(
        style={"height": "80vh", "overflowY": "auto"},
        children=[
            wcc.Selectors(
                label="Selectors",
                children=[
                    ensemble_selector(parent=parent, tab="delta"),
                    delta_ensemble_selector(parent=parent, tab="delta"),
                    property_selector(parent=parent, tab="delta"),
                    source_selector(parent=parent, tab="delta"),
                ],
            ),
            wcc.Selectors(
                label="Filters", children=[filter_selector(parent=parent, tab="delta")]
            ),
        ],
    )


def delta_avg_view() -> html.Div:
    return wcc.FlexColumn(
        children=[],
    )


def property_delta_view(parent: "PropertyStatistics") -> wcc.FlexBox:
    table_surf_options = [{"label": "Table view", "value": "table"}]
    if parent.surface_folders is not None:
        table_surf_options.append(
            {"label": "Surface view (click on bar in chart)", "value": "surface"}
        )
    return wcc.FlexBox(
        style={"margin": "20px"},
        children=[
            wcc.FlexColumn(children=selector_view(parent=parent)),
            wcc.FlexColumn(
                flex=4,
                children=wcc.Frame(
                    color="white",
                    highlight=False,
                    style={"height": "80vh"},
                    children=[
                        wcc.RadioItems(
                            vertical=False,
                            id=parent.uuid("delta-sort"),
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
                            id=parent.uuid("delta-bar-graph"),
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
                            id=parent.uuid("delta-switch-table-surface"),
                            vertical=False,
                            options=table_surf_options,
                            value="table",
                        ),
                        html.Div(id=parent.uuid("delta-table-surface-wrapper")),
                    ],
                ),
            ),
        ],
    )


def table_view(data: List[Any], columns: List[Any]) -> html.Div:
    return html.Div(
        style={"fontSize": "1rem"},
        children=dash_table.DataTable(
            sort_action="native",
            page_action="native",
            filter_action="native",
            style_table={
                "height": "74vh",
                "overflow": "auto",
            },
            data=data,
            columns=columns,
        ),
    )
