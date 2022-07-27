from typing import Callable, Dict, List, Optional

import webviz_core_components as wcc
from dash import html
from webviz_subsurface_components import LeafletMap


def intersection_and_map_layout(get_uuid: Callable) -> html.Div:
    """Layout for the intersection graph and maps"""
    return html.Div(
        children=[
            wcc.Frame(
                highlight=False,
                color="white",
                children=[
                    wcc.Graph(
                        style={"height": "48vh", "background-color": "white"},
                        id=get_uuid("intersection-graph"),
                    ),
                ],
            ),
            wcc.Frame(
                id=get_uuid("maps-and-uncertainty-table-wrapper"),
                highlight=False,
                color="white",
                children=[
                    wcc.FlexBox(
                        style={"height": "40vh", "display": "flex"},
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
        children=[
            html.Label(
                style={"textAlign": "center", "fontSize": "0.8em"},
                id={"id": uuid, "element": "label"},
            ),
            html.Div(
                style={
                    "height": "37vh",
                },
                children=LeafletMap(
                    syncedMaps=synced_uuids,
                    id=leaflet_id,
                    layers=[],
                    unitScale={},
                    autoScaleMap=True,
                    minZoom=-19,
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
