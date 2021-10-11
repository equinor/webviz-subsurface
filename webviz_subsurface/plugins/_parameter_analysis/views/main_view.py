from typing import Callable

import webviz_core_components as wcc
from dash import html
from webviz_config import WebvizConfigTheme

from ..models import ParametersModel, SimulationTimeSeriesModel
from .parameter_qc_view import parameter_qc_view
from .parameter_response_view import parameter_response_view


def main_view(
    get_uuid: Callable,
    vectormodel: SimulationTimeSeriesModel,
    parametermodel: ParametersModel,
    parameterfilter_layout: html.Div,
    theme: WebvizConfigTheme,
) -> wcc.Tabs:
    tabs = [
        wcc.Tab(
            label="Parameter distributions",
            value="tab-1",
            children=parameter_qc_view(
                get_uuid=get_uuid, parametermodel=parametermodel
            ),
        )
    ]

    if vectormodel is not None:
        tabs.append(
            wcc.Tab(
                label="Parameters impact on simulation profiles",
                value="tab-2",
                children=parameter_response_view(
                    get_uuid=get_uuid,
                    parametermodel=parametermodel,
                    parameterfilter_layout=parameterfilter_layout,
                    vectormodel=vectormodel,
                    theme=theme,
                ),
            )
        )

    return wcc.Tabs(
        value="tab-1" if vectormodel is None else "tab-2",
        style={"width": "100%"},
        children=tabs,
    )
