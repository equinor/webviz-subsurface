from typing import Optional, List, Dict, Callable, Tuple
import plotly.graph_objects as go
import plotly.express as px
import dash
from dash.dependencies import Input, Output, State, MATCH, ALL, ClientsideFunction
from dash.exceptions import PreventUpdate

from webviz_subsurface._models import EnsembleTableModelSet
from ..figures.plotly_line_plot import PlotlyLinePlot


def main_controller(
    app: dash.Dash, get_uuid: Callable, tablemodel: EnsembleTableModelSet
) -> None:
    @app.callback(
        Output(get_uuid("graph-store"), "data"),
        Input({"id": get_uuid("selectors"), "attribute": ALL}, "value"),
    )
    def _update_plot(_selectors: List) -> go.Figure:
        ensemble_name = get_value_for_callback_context(
            dash.callback_context.inputs_list, "ensemble"
        )
        x_column_name = get_value_for_callback_context(
            dash.callback_context.inputs_list, "x_selector"
        )

        y_column_name = get_value_for_callback_context(
            dash.callback_context.inputs_list, "y_selector"
        )
        if ensemble_name is None or x_column_name is None or y_column_name is None:
            raise PreventUpdate
        table = tablemodel.ensemble(ensemble_name)
        figure = PlotlyLinePlot()
        figure.add_line(
            x=table.get_column_values_numpy(x_column_name)[0],
            y=table.get_column_values_numpy(y_column_name)[0],
        )
        return figure.figure

    app.clientside_callback(
        ClientsideFunction(namespace="clientside", function_name="update_figure"),
        Output(get_uuid("graph"), "figure"),
        Input(get_uuid("graph-store"), "data"),
        Input({"id": get_uuid("selectors"), "attribute": "x_scale"}, "value"),
        Input({"id": get_uuid("selectors"), "attribute": "y_scale"}, "value"),
    )

    @app.callback(
        Output({"id": get_uuid("selectors"), "attribute": "x_selector"}, "options"),
        Output({"id": get_uuid("selectors"), "attribute": "x_selector"}, "value"),
        Output({"id": get_uuid("selectors"), "attribute": "y_selector"}, "options"),
        Output({"id": get_uuid("selectors"), "attribute": "y_selector"}, "value"),
        Input({"id": get_uuid("selectors"), "attribute": "ensemble"}, "value"),
        State({"id": get_uuid("selectors"), "attribute": "x_selector"}, "value"),
        State({"id": get_uuid("selectors"), "attribute": "y_selector"}, "value"),
    )
    def _update_selectors(
        ensemble_name: str, current_x: Optional[str], current_y: Optional[str]
    ) -> Tuple[List[dict], str, List[dict], str]:
        columns = tablemodel.ensemble(ensemble_name).column_names()
        current_x = current_x if current_x in columns else columns[0]
        current_y = current_y if current_y in columns else columns[0]
        return (
            [{"label": col, "value": col} for col in columns],
            current_x,
            [{"label": col, "value": col} for col in columns],
            current_y,
        )


def get_value_for_callback_context(
    contexts: List[List[Dict]], context_value: str
) -> Optional[str]:
    for context in contexts[0]:
        if context["id"]["attribute"] == context_value:
            return context["value"]
    return None
