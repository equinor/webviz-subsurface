from typing import Callable

from dash import dcc, html


# pylint: disable = too-few-public-methods
class ClientsideStoreElements:
    WELL_OVERVIEW_CHART_SELECTED = "well-overview-chart-selected"


def clientside_stores(get_uuid: Callable) -> html.Div:
    """Contains the clientside stores"""
    return html.Div(
        children=[
            dcc.Store(
                id=get_uuid(ClientsideStoreElements.WELL_OVERVIEW_CHART_SELECTED),
                storage_type="session",
            ),
        ]
    )
