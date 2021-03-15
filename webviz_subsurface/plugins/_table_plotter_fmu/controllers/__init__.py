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
    )
    def _update_plot(_selectors: List) -> go.Figure:

        ensemble_names = get_value_for_callback_context(
            dash.callback_context.inputs_list, "ensemble"
        )
        x_column_name = get_value_for_callback_context(
            dash.callback_context.inputs_list, "x"
        )

        y_column_name = get_value_for_callback_context(
            dash.callback_context.inputs_list, "y"
        )

        if ensemble_names is None or x_column_name is None or y_column_name is None:
            raise PreventUpdate
        dfs = []
        for ens in ensemble_names:
            col_dfs = []
            table = tablemodel.ensemble(ens)
            col_df = table.get_columns_values_df([x_column_name, y_column_name])

            col_df["ENSEMBLE"] = ens
            dfs.append(col_df)
        df = pd.concat(dfs)
        figure = px.line(
            df, x=x_column_name, y=y_column_name, color="ENSEMBLE", line_group="REAL"
        )
        # figure.update_layout(
        #     updatemenus=[
        #         dict(
        #             buttons=list(
        #                 [
        #                     dict(
        #                         args=[{"xaxis": {"autorange": True}}],
        #                         label="Normal",
        #                         method="relayout",
        #                     ),
        #                     dict(
        #                         args=[{"xaxis": {"autorange": "reversed"}}],
        #                         label="Reversed",
        #                         method="relayout",
        #                     ),
        #                 ]
        #             ),
        #             direction="down",
        #             pad={"r": 10, "t": 10},
        #             showactive=True,
        #             active=1,
        #             x=0.1,
        #             xanchor="left",
        #             y=1.08,
        #             yanchor="top",
        #         ),
        #         dict(
        #             buttons=list(
        #                 [
        #                     dict(
        #                         args=[{"yaxis": {"autorange": "True"}}],
        #                         label="Normal",
        #                         method="relayout",
        #                     ),
        #                     dict(
        #                         args=[{"yaxis": {"autorange": "reversed"}}],
        #                         label="Reversed",
        #                         method="relayout",
        #                     ),
        #                 ]
        #             ),
        #             direction="down",
        #             pad={"r": 10, "t": 10},
        #             showactive=True,
        #             x=0.37,
        #             xanchor="left",
        #             y=1.08,
        #             yanchor="top",
        #         ),
        #         dict(
        #             buttons=list(
        #                 [
        #                     dict(
        #                         args=[{"contours.showlines": False, "type": "contour"}],
        #                         label="Hide lines",
        #                         method="restyle",
        #                     ),
        #                     dict(
        #                         args=[{"contours.showlines": True, "type": "contour"}],
        #                         label="Show lines",
        #                         method="restyle",
        #                     ),
        #                 ]
        #             ),
        #             direction="down",
        #             pad={"r": 10, "t": 10},
        #             showactive=True,
        #             x=0.58,
        #             xanchor="left",
        #             y=1.08,
        #             yanchor="top",
        #         ),
        #     ]
        # )
        # figure.update_layout(
        #     annotations=[
        #         dict(
        #             text="X-axis range",
        #             x=0,
        #             xref="paper",
        #             y=1.07,
        #             yref="paper",
        #             align="left",
        #             showarrow=False,
        #         ),
        #         dict(
        #             text="Y-axis range",
        #             x=0.25,
        #             xref="paper",
        #             y=1.07,
        #             yref="paper",
        #             showarrow=False,
        #         ),
        #     ]
        # )

        observations = observationmodel.get_observations_for_attribute(y_column_name)
        if observations is not None:
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
        # return figure.figure

    @app.callback(
        Output(
            {"id": get_uuid("clientside"), "plotly_attribute": "plotly_layout"}, "data"
        ),
        Input({"id": get_uuid("plotly_layout"), "layout_attribute": ALL}, "value"),
    )
    def _update_layout(layout_attributes):
        """Store plotly layout options from user selections in a dcc.Store"""
        print(layout_attributes)
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
        Output({"id": get_uuid("plotly_data"), "data_attribute": "x"}, "options"),
        Output({"id": get_uuid("plotly_data"), "data_attribute": "x"}, "value"),
        Output({"id": get_uuid("plotly_data"), "data_attribute": "y"}, "options"),
        Output({"id": get_uuid("plotly_data"), "data_attribute": "y"}, "value"),
        Input({"id": get_uuid("plotly_data"), "data_attribute": "ensemble"}, "value"),
        State({"id": get_uuid("plotly_data"), "data_attribute": "x"}, "value"),
        State({"id": get_uuid("plotly_data"), "data_attribute": "y"}, "value"),
    )
    def _update_selectors(
        ensemble_name: str, current_x: Optional[str], current_y: Optional[str]
    ) -> Tuple[List[dict], str, List[dict], str]:
        columns = tablemodel.ensemble(ensemble_name[0]).column_names()
        current_x = current_x if current_x in columns else columns[0]
        current_y = current_y if current_y in columns else columns[-1]
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
        if context["id"]["data_attribute"] == context_value:
            return context["value"]
    return None
