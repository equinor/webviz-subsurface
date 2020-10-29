import dash_html_components as html
import dash_core_components as dcc
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


def surface_select_view(parent, tab: str) -> html.Div:
    return html.Div(
        id=parent.uuid("surface-select"),
        style={"width": "75%"},
        children=[
            html.Label("Surface statistics"),
            dcc.Dropdown(
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
                persistence=True,
                persistence_type="session",
            ),
        ],
    )


def surface_view(
    parent, ensemble: str, layers: list, synced_ids: list = None
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
            minZoom=-5,
            updateMode="replace",
            mouseCoords={"position": "bottomright"},
            colorBar={"position": "bottomleft"},
        ),
    )


# pylint: disable=too-many-arguments
def surface_views(
    parent,
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
            html.P(
                style={"margin": "0px", "fontSize": "2vh"},
                children=f"{statistic} for {prop}, {zone} in {ensemble}",
            ),
            surface_view(
                parent=parent,
                ensemble=ensemble,
                synced_ids=[delta_ensemble, "diff"],
                layers=[ens_layer],
            ),
            html.P(
                style={"margin": "0px", "fontSize": "2vh"},
                children=f"{statistic} for {prop}, {zone} in {delta_ensemble}",
            ),
            surface_view(
                parent=parent,
                ensemble=delta_ensemble,
                synced_ids=[ensemble, "diff"],
                layers=[delta_ens_layer],
            ),
            html.P(
                style={"margin": "0px", "fontSize": "2vh"},
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


def selector_view(parent) -> html.Div:
    return html.Div(
        style={"height": "80vh", "overflowY": "auto"},
        className="framed",
        children=[
            html.Div(
                children=[
                    ensemble_selector(parent=parent, tab="delta"),
                    delta_ensemble_selector(parent=parent, tab="delta"),
                ]
            ),
            property_selector(parent=parent, tab="delta"),
            source_selector(parent=parent, tab="delta"),
            filter_selector(parent=parent, tab="delta"),
        ],
    )


def delta_avg_view() -> html.Div:
    return html.Div(
        style={"flex": 1},
        children=[],
    )


def property_delta_view(parent) -> wcc.FlexBox:
    table_surf_options = [{"label": "Table view", "value": "table"}]
    if parent.surface_folders is not None:
        table_surf_options.append(
            {"label": "Surface view (click on bar in chart)", "value": "surface"}
        )
    return wcc.FlexBox(
        style={"margin": "20px"},
        children=[
            html.Div(style={"flex": 1}, children=selector_view(parent=parent)),
            html.Div(
                style={"flex": 4, "height": "80vh"},
                className="framed",
                children=[
                    dcc.RadioItems(
                        id=parent.uuid("delta-sort"),
                        options=[
                            {"label": "Sort by Average", "value": "Avg"},
                            {"label": "Sort by Standard Deviation", "value": "Stddev"},
                        ],
                        value="Avg",
                        labelStyle={
                            "display": "inline-block",
                            "margin": "5px",
                        },
                        persistence=True,
                        persistence_type="session",
                    ),
                    wcc.Graph(
                        id=parent.uuid("delta-bar-graph"),
                        config={"displayModeBar": False},
                        style={"height": "75vh"},
                    ),
                ],
            ),
            html.Div(
                style={"flex": 4, "height": "80vh"},
                className="framed",
                children=[
                    dcc.RadioItems(
                        id=parent.uuid("delta-switch-table-surface"),
                        options=table_surf_options,
                        value="table",
                        labelStyle={
                            "display": "inline-block",
                            "margin": "5px",
                        },
                        persistence=True,
                        persistence_type="session",
                    ),
                    html.Div(id=parent.uuid("delta-table-surface-wrapper")),
                ],
            ),
        ],
    )


def table_view(data, columns) -> html.Div:
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
