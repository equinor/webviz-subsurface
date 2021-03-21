from typing import Optional, List, Dict, Callable, Tuple
import json

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import dash
from dash.dependencies import Input, Output, State, MATCH, ALL, ClientsideFunction
from dash.exceptions import PreventUpdate

from webviz_subsurface._models import (
    EnsembleTableModelSet,
    ObservationModel,
    ParametersModel,
)
from ..figures.plotly_line_plot import PlotlyLinePlot


def main_controller(
    app: dash.Dash,
    get_uuid: Callable,
    tablemodel: EnsembleTableModelSet,
    observationmodel: ObservationModel,
    parametermodel: ParametersModel,
) -> None:
    @app.callback(
        Output(
            {"id": get_uuid("clientside"), "plotly_attribute": "plotly_data"}, "data"
        ),
        Output(
            {"id": get_uuid("clientside"), "plotly_attribute": "initial_layout"}, "data"
        ),
        Input(
            {"id": get_uuid("plotly_data"), "data_attribute": ALL, "source": "table"},
            "value",
        ),
        Input(
            {
                "id": get_uuid("plotly_data"),
                "data_attribute": ALL,
                "source": "parameters",
            },
            "value",
        ),
        Input(
            {
                "id": get_uuid("data_selectors"),
                "data_attribute": "ensemble",
                "source": "table",
            },
            "value",
        ),
        Input(get_uuid("aggregate"), "value"),
        Input(get_uuid("group_level1"), "value"),
    )
    def _update_plot(
        _table_selectors: List,
        _parameter_selectors: List,
        ensemble_names: List,
        aggregation: str,
        group: List,
    ) -> go.Figure:
        data_attrs = {}
        parameter_attrs = {}
        # Find attribute names and values
        for ctx in dash.callback_context.inputs_list[0]:
            if ctx["value"] is not None:
                data_attrs[ctx["id"]["data_attribute"]] = ctx["value"]
        # Find attribute names and values
        for ctx in dash.callback_context.inputs_list[1]:
            if ctx["value"] is not None:
                parameter_attrs[ctx["id"]["data_attribute"]] = ctx["value"]
        # Prevent update is no data is selected
        if ensemble_names is None or all(list(data_attrs.values())) is None:
            raise PreventUpdate
        dfs = []

        # Retrieve table data for each ensemble and aggregate
        for ens in ensemble_names:
            col_dfs = []
            table = tablemodel.ensemble(ens)
            columns = list(set(data_attrs.values()))
            columns = [col for col in columns if col != "REAL"]
            col_df = table.get_columns_values_df(columns)
            col_df["ENSEMBLE"] = ens
            dfs.append(col_df)
        data_df = pd.concat(dfs)
        dfs = []
        # Retrieve parameter data for each ensemble and aggregate
        for ens in ensemble_names:
            col_dfs = []
            table = parametermodel.ensemble(ens)
            columns = list(set(parameter_attrs.values()))
            columns = [col for col in columns if col != "REAL"]
            col_df = table.get_columns_values_df(columns)
            col_df["ENSEMBLE"] = ens
            dfs.append(col_df)
        parameter_df = pd.concat(dfs)

        df = pd.merge(data_df, parameter_df, on=["ENSEMBLE", "REAL"])
        y_column_name = get_value_for_callback_context(
            dash.callback_context.inputs_list, "y"
        )
        x_column_name = get_value_for_callback_context(
            dash.callback_context.inputs_list, "x"
        )
        print(df)
        if group is not None:
            group_cols = group

        else:
            group_cols = ["ENSEMBLE"]
        print(df.columns)
        # df = df.groupby(group_cols)
        # if aggregation is not None:
        #     df = df.agg({y_column_name: aggregation})
        # df = df.agg({y_column_name: "mean"})
        # df = df.reset_index()
        # Create plotly express figure from data and active attributes
        # figure = PlotlyLinePlot()
        # figure.add_realization_traces(
        #     df, x_column_name, y_column_name, group_cols, aggregation=aggregation
        # )
        df["label"] = df.agg(
            lambda x: " | ".join([f"{x[sel]}" for sel in group_cols]), axis=1
        )
        figure = px.line(
            df,
            color="label",
            line_group="label",
            color_discrete_sequence=px.colors.sequential.Plasma_r,
            **data_attrs,
            **parameter_attrs,
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

        return figure["data"], figure["layout"]

    @app.callback(
        Output(
            {"id": get_uuid("clientside"), "plotly_attribute": "update_layout"}, "data"
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
        Output(
            {"id": get_uuid("clientside"), "plotly_attribute": "plotly_layout"}, "data"
        ),
        Input(
            {"id": get_uuid("clientside"), "plotly_attribute": "initial_layout"}, "data"
        ),
        Input(
            {"id": get_uuid("clientside"), "plotly_attribute": "update_layout"}, "data"
        ),
    )
    def _update_plot_layout(initial_layout: dict, update_layout: dict):
        if initial_layout is None:
            raise PreventUpdate
        fig = go.Figure({"layout": initial_layout})
        if update_layout is not None:
            fig.update_layout(update_layout)
        return fig["layout"]

    app.clientside_callback(
        ClientsideFunction(namespace="clientside", function_name="update_figure"),
        Output(get_uuid("graph"), "figure"),
        Input(
            {"id": get_uuid("clientside"), "plotly_attribute": "plotly_data"}, "data"
        ),
        Input(
            {"id": get_uuid("clientside"), "plotly_attribute": "plotly_layout"}, "data"
        ),
        Input(
            {"id": get_uuid("clientside"), "plotly_attribute": "plotly_graph"}, "data"
        ),
    )


def get_value_for_callback_context(
    contexts: List[List[Dict]], context_value: str
) -> Optional[str]:
    for context in contexts[0]:
        if context["id"]["data_attribute"] == context_value:
            return context["value"]
    return None
