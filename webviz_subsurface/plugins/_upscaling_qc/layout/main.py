from typing import Callable

from dash import html
import webviz_core_components as wcc


def main(get_uuid: Callable) -> html.Div:
    return html.Div(wcc.Graph(id=get_uuid("plotly-graph")))
