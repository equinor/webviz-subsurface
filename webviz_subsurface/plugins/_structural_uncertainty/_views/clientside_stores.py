from typing import Callable, Dict, List, Union

from dash import dcc, html


def clientside_stores(
    get_uuid: Callable,
    initial_settings: Dict,
    realizations: List[Union[str, int]],
) -> html.Div:
    """Contains the clientside stores"""
    return html.Div(
        children=[
            dcc.Store(
                id=get_uuid("intersection-graph-data"), storage_type="session", data=[]
            ),
            dcc.Store(
                id=get_uuid("initial-intersection-graph-layout"),
                data=initial_settings.get("intersection_layout", {}),
            ),
            dcc.Store(
                id=get_uuid("realization-store"),
                data=initial_settings.get("intersection-data", {}).get(
                    "realizations", realizations
                ),
            ),
            dcc.Store(
                id={"id": get_uuid("map"), "element": "stored_polyline"},
                storage_type="session",
            ),
            dcc.Store(
                id={"id": get_uuid("map"), "element": "stored_xline"},
                storage_type="session",
            ),
            dcc.Store(
                id={"id": get_uuid("map"), "element": "stored_yline"},
                storage_type="session",
            ),
            dcc.Store(
                id=get_uuid("intersection-graph-layout"),
                storage_type="session",
            ),
            dcc.Store(
                id={
                    "id": get_uuid("intersection-data"),
                    "element": "stored_manual_update_options",
                },
                storage_type="session",
            ),
            dcc.Store(
                id=get_uuid("map-color-ranges"),
                storage_type="session",
            ),
        ]
    )
