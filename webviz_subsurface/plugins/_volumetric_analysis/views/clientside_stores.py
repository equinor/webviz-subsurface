from typing import Callable

import dash_core_components as dcc
import dash_html_components as html


def clientside_stores(get_uuid: Callable) -> html.Div:
    """Contains the clientside stores"""
    return html.Div(
        children=[
            dcc.Store(id=get_uuid("filter-voldist"), storage_type="session"),
            dcc.Store(id=get_uuid("selections-voldist"), storage_type="session"),
            dcc.Store(id=get_uuid("page-selected-voldist"), storage_type="session"),
        ]
    )
