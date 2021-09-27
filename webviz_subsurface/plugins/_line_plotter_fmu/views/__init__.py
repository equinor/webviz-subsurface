from typing import Callable, Dict, List

import webviz_core_components as wcc
from dash import dcc, html

from .data_selectors_view import data_selectors_view
from .plot_options_view import plot_options_view
from .plot_traces_view import highlight_realizations_view, line_traces_view


def main_view(
    get_uuid: Callable,
    ensemble_names: List[str],
    data_column_names: List[str],
    parameter_names: List[str],
    realizations: List[int],
    initial_data: Dict,
    initial_layout: Dict,
) -> html.Div:

    return wcc.FlexBox(
        children=[
            wcc.Frame(
                style={"flex": 1, "height": "90vh"},
                children=[
                    data_stores(get_uuid=get_uuid),
                    data_selectors_view(
                        get_uuid=get_uuid,
                        ensemble_names=ensemble_names,
                        data_column_names=data_column_names,
                        parameter_names=parameter_names,
                        initial_data=initial_data,
                    ),
                    line_traces_view(
                        get_uuid=get_uuid,
                    ),
                    highlight_realizations_view(
                        get_uuid=get_uuid, realizations=realizations
                    ),
                    plot_options_view(get_uuid=get_uuid, initial_layout=initial_layout),
                ],
            ),
            wcc.Frame(
                style={"flex": 5, "height": "90vh"},
                color="white",
                highlight=False,
                children=wcc.Graph(style={"height": "86vh"}, id=get_uuid("graph")),
            ),
        ]
    )


def data_stores(get_uuid: Callable) -> html.Div:
    return html.Div(
        [
            dcc.Store(
                id={"id": get_uuid("clientside"), "plotly_attribute": "plotly_graph"},
                data=get_uuid("graph"),
            ),
            dcc.Store(
                id={"id": get_uuid("clientside"), "plotly_attribute": "plotly_data"}
            ),
            dcc.Store(
                id={
                    "id": get_uuid("clientside"),
                    "plotly_attribute": "plotly_layout",
                }
            ),
            dcc.Store(
                id={
                    "id": get_uuid("clientside"),
                    "plotly_attribute": "initial_layout",
                }
            ),
            dcc.Store(
                id={
                    "id": get_uuid("clientside"),
                    "plotly_attribute": "update_layout",
                }
            ),
            dcc.Store(id=get_uuid("stored_x_value")),
        ]
    )
