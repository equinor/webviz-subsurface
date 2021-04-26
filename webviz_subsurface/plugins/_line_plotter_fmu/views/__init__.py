from typing import Callable, Union, List, Dict
from pathlib import Path

import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_config.webviz_assets import WEBVIZ_ASSETS

import webviz_subsurface
from .plot_options_view import plot_options_view
from .data_selectors_view import data_selectors_view
from .group_and_filter_selectors import group_by_view


def main_view(
    get_uuid: Callable,
    ensemble_names=List[str],
    data_column_names=List[str],
    parameter_names=List[str],
    initial_data=Dict,
    initial_layout=Dict,
) -> html.Div:
    WEBVIZ_ASSETS.add(
        Path(webviz_subsurface.__file__).parent / "_assets" / "css" / "container.css"
    )
    return wcc.FlexBox(
        children=[
            html.Div(
                style={"flex": 1, "height": "89vh"},
                children=[
                    data_stores(get_uuid=get_uuid),
                    data_selectors_view(
                        get_uuid=get_uuid,
                        ensemble_names=ensemble_names,
                        data_column_names=data_column_names,
                        parameter_names=parameter_names,
                        initial_data=initial_data,
                    ),
                    group_by_view(
                        get_uuid=get_uuid,
                    ),
                    plot_options_view(get_uuid=get_uuid),
                ],
            ),
            html.Div(
                className="framed",
                style={"flex": 5, "height": "89vh"},
                children=[plot_view(get_uuid=get_uuid)],
            ),
        ]
    )


def plot_view(get_uuid: Callable) -> html.Div:
    return html.Div(
        [
            wcc.FlexBox(
                style={"height": "88vh"},
                children=[
                    wcc.Graph(id=get_uuid("graph")),
                ],
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
            dcc.Store(id={"id": get_uuid("clientside"), "attribute": "single_real"}),
        ]
    )
