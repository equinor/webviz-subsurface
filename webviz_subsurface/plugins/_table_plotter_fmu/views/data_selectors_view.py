from typing import Callable, Union, List, Dict
from pathlib import Path

import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_subsurface._models import EnsembleTableModelSet


def data_selectors_view(
    get_uuid: Callable, tablemodel: EnsembleTableModelSet
) -> html.Div:
    return html.Div(
        className="framed",
        children=[
            html.H5("Data selectors"),
            dropdown_for_plotly_data(
                uuid=get_uuid("data_selectors"),
                data_attribute="ensemble",
                title="Ensemble",
                options=[
                    {"label": ens, "value": ens} for ens in tablemodel.ensemble_names()
                ],
                value=[tablemodel.ensemble_names()[0]],
                multi=True,
            ),
            dropdown_for_plotly_data(
                uuid=get_uuid("plotly_data"),
                data_attribute="x",
                title="X-value",
                options=[],
            ),
            dropdown_for_plotly_data(
                uuid=get_uuid("plotly_data"),
                data_attribute="y",
                title="Y-value",
                options=[],
            ),
            dropdown_for_plotly_data(
                uuid=get_uuid("plotly_data"),
                data_attribute="color",
                title="Color",
                options=[],
                value=None,
                clearable=True,
            ),
        ],
    )


def dropdown_for_plotly_data(
    uuid: str,
    data_attribute: str,
    title: str,
    options: List[Dict],
    value: Union[List, str] = None,
    flex: int = 1,
    placeholder: str = "Select...",
    multi=False,
    clearable=False,
) -> html.Div:
    return html.Div(
        style={"flex": flex},
        children=[
            html.Label(title),
            dcc.Dropdown(
                id={
                    "id": uuid,
                    "data_attribute": data_attribute,
                },
                options=options,
                value=value,
                clearable=clearable,
                placeholder=placeholder,
                multi=multi,
            ),
        ],
    )