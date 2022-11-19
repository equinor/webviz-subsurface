from typing import Callable

from dash import dcc, html


def clientside_stores(get_uuid: Callable) -> html.Div:
    """Contains the clientside stores"""
    return html.Div(
        children=[
            dcc.Store(id=get_uuid("selections"), storage_type="session"),
            dcc.Store(id=get_uuid("page-selected"), storage_type="session"),
            dcc.Store(id=get_uuid("voldist-page-selected"), storage_type="session"),
            dcc.Store(id=get_uuid("initial-load-info"), storage_type="memory"),
            html.Div(
                style={"display": "none"},
                children=dcc.Download(id=get_uuid("download-dataframe")),
            ),
        ]
    )
