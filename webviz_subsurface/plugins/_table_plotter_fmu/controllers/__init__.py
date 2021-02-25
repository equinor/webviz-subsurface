from typing import Optional, List, Dict
import plotly.express as px
import dash
from dash.dependencies import Input, Output, State, MATCH, ALL
from dash.exceptions import PreventUpdate


def main_controller(parent, app):
    @app.callback(
        Output(parent.uuid("graph"), "figure"),
        Input({"id": parent.uuid("selectors"), "attribute": ALL}, "value"),
    )
    def update_plot(selectors):
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
        table = parent.tablemodel.ensemble(ensemble_name)
        print(table.get_column_values_df(x_column_name))
        return px.line(
            x=table.get_column_values_df(x_column_name)[x_column_name],
            y=table.get_column_values_df(y_column_name)[y_column_name],
        )

    @app.callback(
        Output({"id": parent.uuid("selectors"), "attribute": "x_selector"}, "options"),
        Output({"id": parent.uuid("selectors"), "attribute": "x_selector"}, "value"),
        Output({"id": parent.uuid("selectors"), "attribute": "y_selector"}, "options"),
        Output({"id": parent.uuid("selectors"), "attribute": "y_selector"}, "value"),
        Input({"id": parent.uuid("selectors"), "attribute": "ensemble"}, "value"),
        State({"id": parent.uuid("selectors"), "attribute": "x_selector"}, "value"),
        State({"id": parent.uuid("selectors"), "attribute": "y_selector"}, "value"),
    )
    def update_selectors(
        ensemble_name: str, current_x: Optional[str], current_y: Optional[str]
    ):
        columns = parent.tablemodel.ensemble(ensemble_name).column_names()
        current_x = current_x if current_x in columns else columns[0]
        current_y = current_y if current_y in columns else columns[0]
        return (
            [{"label": col, "value": col} for col in columns],
            current_x,
            [{"label": col, "value": col} for col in columns],
            current_y,
        )


def get_value_for_callback_context(contexts: List[List[Dict]], context_value: str):
    for context in contexts[0]:
        if context["id"]["attribute"] == context_value:
            return context["value"]
    return None
