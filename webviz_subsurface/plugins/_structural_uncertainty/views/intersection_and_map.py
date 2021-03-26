from typing import Callable, Optional, List, Dict
import dash_html_components as html
import webviz_core_components as wcc
from webviz_subsurface_components import LeafletMap
from .uncertainty_table import uncertainty_table_layout


def intersection_and_map_layout(get_uuid: Callable) -> html.Div:
    """Layout for the intersection graph and maps"""
    return html.Div(
        children=[
            html.Div(
                className="framed",
                children=[
                    wcc.Graph(
                        style={"height": "48vh", "background-color": "white"},
                        id=get_uuid("intersection-graph"),
                    ),
                ],
            ),
            html.Div(
                id=get_uuid("maps-and-uncertainty-table-wrapper"),
                style={"background-color": "white"},
                children=[
                    wcc.FlexBox(
                        style={"height": "40vh", "display": "flex"},
                        className="framed",
                        id=get_uuid("all-maps-wrapper"),
                        children=[
                            html.Div(
                                style={"flex": 1},
                                id=get_uuid("map-wrapper"),
                                children=map_layout(
                                    uuid=get_uuid("map"),
                                    leaflet_id=get_uuid("leaflet-map1"),
                                    synced_uuids=[
                                        get_uuid("leaflet-map2"),
                                        get_uuid("leaflet-map3"),
                                    ],
                                    draw_polyline=True,
                                ),
                            ),
                            html.Div(
                                style={"flex": 1},
                                children=map_layout(
                                    uuid=get_uuid("map2"),
                                    leaflet_id=get_uuid("leaflet-map2"),
                                    synced_uuids=[
                                        get_uuid("leaflet-map1"),
                                        get_uuid("leaflet-map3"),
                                    ],
                                ),
                            ),
                            html.Div(
                                style={"flex": 1},
                                children=map_layout(
                                    uuid=get_uuid("map3"),
                                    leaflet_id=get_uuid("leaflet-map3"),
                                    synced_uuids=[
                                        get_uuid("leaflet-map1"),
                                        get_uuid("leaflet-map2"),
                                    ],
                                ),
                            ),
                        ],
                    ),
                    html.Div(
                        id={
                            "id": get_uuid("uncertainty-table"),
                            "element": "wrapper",
                        },
                        className="framed",
                        style={"height": "40vh", "display": "none"},
                        children=uncertainty_table_layout(
                            uuid=get_uuid("uncertainty-table"),
                        ),
                    ),
                ],
            ),
        ],
    )


def map_layout(
    uuid: str,
    leaflet_id: str,
    synced_uuids: Optional[List[str]] = None,
    draw_polyline: bool = False,
) -> html.Div:
    synced_uuids = synced_uuids if synced_uuids else []
    props: Optional[Dict] = (
        {
            "drawTools": {
                "drawMarker": False,
                "drawPolygon": False,
                "drawPolyline": True,
                "position": "topright",
            }
        }
        if draw_polyline
        else {}
    )
    return html.Div(
        style={"height": "100%", "padding": "10px"},
        children=[
            html.Label(
                style={"textAlign": "center", "fontSize": "0.8em"},
                id={"id": uuid, "element": "label"},
            ),
            html.Div(
                style={
                    "height": "38vh",
                },
                children=LeafletMap(
                    syncedMaps=synced_uuids,
                    id=leaflet_id,
                    layers=[],
                    unitScale={},
                    autoScaleMap=True,
                    minZoom=-5,
                    updateMode="replace",
                    mouseCoords={"position": "bottomright"},
                    colorBar={"position": "bottomleft"},
                    switch={
                        "value": False,
                        "disabled": False,
                        "label": "Hillshading",
                    },
                    **props
                ),
            ),
        ],
    )
