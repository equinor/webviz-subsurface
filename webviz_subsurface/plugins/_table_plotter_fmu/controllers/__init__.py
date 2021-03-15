from typing import Optional, List, Dict, Callable, Tuple
import json

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import dash
from dash.dependencies import Input, Output, State, MATCH, ALL, ClientsideFunction
from dash.exceptions import PreventUpdate

from webviz_subsurface._models import EnsembleTableModelSet, ObservationModel
from ..figures.plotly_line_plot import PlotlyLinePlot


def main_controller(
    app: dash.Dash,
    get_uuid: Callable,
    tablemodel: EnsembleTableModelSet,
    observationmodel: ObservationModel,
) -> None:
    @app.callback(
        Output({"id": get_uuid("clientside"), "plotly_attribute": "figure"}, "data"),
        Input({"id": get_uuid("plotly_data"), "data_attribute": ALL}, "value"),
        Input(
            {"id": get_uuid("data_selectors"), "data_attribute": "ensemble"}, "value"
        ),
    )
    def _update_plot(_selectors: List, ensemble_names: List) -> go.Figure:
        attrs = {}
        # Find attribute names and values
        for ctx in dash.callback_context.inputs_list[0]:
            if ctx["value"] is not None:
                attrs[ctx["id"]["data_attribute"]] = ctx["value"]

        # Prevent update is no data is selected
        if ensemble_names is None or any(list(attrs.values())) is None:
            raise PreventUpdate
        dfs = []

        # Retrieve table data for each ensemble and aggregate
        for ens in ensemble_names:
            col_dfs = []
            table = tablemodel.ensemble(ens)
            columns = list(set(attrs.values()))
            columns = [col for col in columns if col != "REAL"]
            print(columns)
            col_df = table.get_columns_values_df(columns)
            col_df["ENSEMBLE"] = ens
            dfs.append(col_df)
        df = pd.concat(dfs)

        # Create plotly express figure from data and active attributes
        figure = px.line(df, line_group="REAL", **attrs)

        # Add observations
        y_column_name = get_value_for_callback_context(
            dash.callback_context.inputs_list, "y"
        )
        observations = observationmodel.get_observations_for_attribute(y_column_name)
        if observations is not None:
            x_column_name = get_value_for_callback_context(
                dash.callback_context.inputs_list, "x"
            )
            [
                figure.add_trace(
                    {
                        "x": [value.get(x_column_name), []],
                        "y": [value.get("value"), []],
                        "marker": {"color": "black"},
                        "text": value.get("comment", None),
                        "hoverinfo": "y+x+text",
                        "showlegend": False,
                        "error_y": {
                            "type": "data",
                            "array": [value.get("error"), []],
                            "visible": True,
                        },
                    }
                )
                for value in observations
            ]

        return figure

    @app.callback(
        Output(
            {"id": get_uuid("clientside"), "plotly_attribute": "plotly_layout"}, "data"
        ),
        Input({"id": get_uuid("plotly_layout"), "layout_attribute": ALL}, "value"),
    )
    def _update_layout(layout_attributes):
        """Store plotly layout options from user selections in a dcc.Store"""
        # print(layout_attributes)
        if layout_attributes is None:
            return {}
        layout = {}
        for ctx in dash.callback_context.inputs_list[0]:
            layout[ctx["id"]["layout_attribute"]] = ctx["value"]
        return layout

    @app.callback(
        Output(get_uuid("graph"), "figure"),
        Input({"id": get_uuid("clientside"), "plotly_attribute": "figure"}, "data"),
        Input(
            {"id": get_uuid("clientside"), "plotly_attribute": "plotly_layout"}, "data"
        ),
    )
    def _update_plot_layout(figure: dict, layout: dict):
        fig = go.Figure(figure)
        if layout is not None:
            fig.update_layout(layout)
        return fig

    @app.callback(
        Output({"id": get_uuid("plotly_data"), "data_attribute": ALL}, "options"),
        Output({"id": get_uuid("plotly_data"), "data_attribute": ALL}, "value"),
        Input(
            {"id": get_uuid("data_selectors"), "data_attribute": "ensemble"}, "value"
        ),
        State({"id": get_uuid("plotly_data"), "data_attribute": ALL}, "value"),
    )
    def _update_selectors(
        ensemble_name: str, current_vals: List
    ) -> Tuple[List[dict], str, List[dict], str]:
        columns = tablemodel.ensemble(ensemble_name[0]).column_names()
        outopts = []
        outvals = []
        outlist = dash.callback_context.outputs_list
        statelist = dash.callback_context.states_list
        for stateval in statelist[0]:
            outopts.append([{"label": col, "value": col} for col in columns + ["REAL"]])
            outvals.append(stateval if stateval in columns + [None] else columns[0])
        return outopts, outvals


def get_value_for_callback_context(
    contexts: List[List[Dict]], context_value: str
) -> Optional[str]:
    for context in contexts[0]:
        if context["id"]["data_attribute"] == context_value:
            return context["value"]
    return None
