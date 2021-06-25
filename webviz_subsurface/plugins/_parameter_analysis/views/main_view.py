from typing import Callable

import dash_html_components as html
import dash_core_components as dcc
from webviz_config import WebvizConfigTheme

import webviz_core_components as wcc
from .parameter_qc_view import parameter_qc_view
from .parameter_response_view import parameter_response_view
from ..models import ParametersModel, SimulationTimeSeriesModel


def main_view(
    get_uuid: Callable,
    vectormodel: SimulationTimeSeriesModel,
    parametermodel: ParametersModel,
    theme: WebvizConfigTheme,
) -> dcc.Tabs:
    tabs = [
        wcc.Tab(
            label="Parameter distributions",
            children=parameter_qc_view(
                get_uuid=get_uuid, parametermodel=parametermodel
            ),
        )
    ]
    if vectormodel is not None:
        tabs.append(
            wcc.Tab(
                label="Parameters impact on simulation profiles",
                children=parameter_response_view(
                    get_uuid=get_uuid,
                    parametermodel=parametermodel,
                    vectormodel=vectormodel,
                    theme=theme,
                ),
            )
        )

    return html.Div(
        id=get_uuid("layout"),
        children=wcc.Tabs(
            style={"width": "100%"},
            children=tabs,
        ),
    )
