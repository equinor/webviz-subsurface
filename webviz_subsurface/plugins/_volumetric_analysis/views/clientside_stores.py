from typing import Callable

import dash_core_components as dcc
import dash_html_components as html


def clientside_stores(get_uuid: Callable) -> html.Div:
    """Contains the clientside stores"""
    return html.Div(
        children=[
            dcc.Store(id=get_uuid("filter-voldist"), storage_type="session"),
            dcc.Store(id=get_uuid("selections"), storage_type="session"),
            dcc.Store(id=get_uuid("page-selected"), storage_type="session"),
            dcc.Store(id=get_uuid("voldist-page-selected"), storage_type="session"),
            dcc.Store(id=get_uuid("test"), storage_type="session"),
            html.Div(
                style={"display": "none"},
                children=dcc.Download(id=get_uuid("download-dataframe")),
            ),
        ]
    )
