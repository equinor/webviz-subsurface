from typing import Callable, Tuple, Union

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, callback_context, no_update
from dash.exceptions import PreventUpdate

from webviz_subsurface._figures import BarChart, ScatterPlot, TimeSeriesFigure
from webviz_subsurface._utils.colors import hex_to_rgba_str, rgba_to_hex
from webviz_subsurface._utils.dataframe_utils import (
    correlate_response_with_dataframe,
    merge_dataframes_on_realization,
)

from .._utils import datetime_utils
from ..models import (
    ParametersModel,
    ProviderTimeSeriesDataModel,
    SimulationTimeSeriesModel,
)


# pylint: disable=too-many-statements
def parameter_response_controller(
    app: Dash,
    get_uuid: Callable,
    vectormodel: Union[SimulationTimeSeriesModel, ProviderTimeSeriesDataModel],
    parametermodel: ParametersModel,
):
    @app.callback(
        Output(get_uuid("vector-vs-time-graph"), "figure"),
        Output(get_uuid("vector-vs-param-scatter"), "figure"),
        Output(get_uuid("vector-corr-graph"), "figure"),
        Output(get_uuid("param-corr-graph"), "figure"),
        Input({"id": get_uuid("ensemble-selector"), "tab": "response"}, "value"),
        Input(get_uuid("vector-selector"), "selectedNodes"),
        Input({"id": get_uuid("parameter-select"), "tab": "response"}, "value"),
        Input(get_uuid("date-selected"), "data"),
        Input(get_uuid("vector-filter-store"), "data"),
        Input(get_uuid("visualization"), "value"),
        Input({"id": get_uuid("plot-options"), "tab": "response"}, "data"),
        Input({"id": get_uuid("parameter-filter"), "type": "data-store"}, "data"),
        State(get_uuid("param-corr-graph"), "figure"),
        State(get_uuid("vector-corr-graph"), "figure"),
    )
    # pylint: disable=too-many-locals, too-many-arguments
    def _update_graphs(
        ensemble: str,
        vector: str,
        parameter: Union[None, dict],
        date: str,
        column_keys: str,
        visualization: str,
        options: str,
        real_filter: dict,
        corr_p_fig: dict,
        corr_v_fig: dict,
    ) -> Tuple[dict, dict, dict, dict]:
        """
        Main callback to update plots. Initially all plots are generated,
        while only relevant plots are updated in subsequent callbacks
        """
        ctx = callback_context.triggered[0]["prop_id"].split(".")[0]
        if not ctx or not vector:
            raise PreventUpdate

        vector = vector[0]
        date = datetime_utils.from_str(date)
        realizations = real_filter[ensemble]
        color = options["color"] if options["color"] is not None else "#007079"

        if len(realizations) <= 1:
            return [empty_figure()] * 4

        filtered_vectors = (
            vectormodel.filter_vectors(column_keys) if column_keys is not None else []
        )
        vectors = list(set(filtered_vectors + [vector]))

        # Get dataframe with vectors and dataframe with parameters and merge
        vector_df = vectormodel.get_vector_df(
            ensemble=ensemble, realizations=realizations, vectors=vectors
        )
        if date not in vector_df["DATE"].values:
            return [empty_figure("Selected date does not exist for ensemble")] * 4
        if vector not in vector_df:
            return [empty_figure("Selected vector does not exist for ensemble")] * 4

        param_df = parametermodel.get_parameter_df_for_ensemble(ensemble, realizations)
        merged_df = merge_dataframes_on_realization(
            dframe1=vector_df[vector_df["DATE"] == date], dframe2=param_df
        )
        # Make correlation figure for vector
        if options["autocompute_corr"]:
            corr_v_fig = make_correlation_figure(
                merged_df, response=vector, corrwith=parametermodel.parameters
            ).figure

        # Get clicked parameter correlation bar or largest bar initially
        parameter = (
            parameter if parameter is not None else corr_v_fig["data"][0]["y"][-1]
        )
        corr_v_fig = color_corr_bars(corr_v_fig, parameter, color, options["opacity"])

        if not filtered_vectors:
            text = (
                "Select vectors for parameter correlation to correlate"
                if not bool(column_keys)
                else "No vectors match selected filter"
            )
            corr_p_fig = empty_figure(text)
        else:
            # Make correlation figure for parameter
            if options["autocompute_corr"]:
                corr_p_fig = make_correlation_figure(
                    merged_df, response=parameter, corrwith=vectors
                ).figure

            corr_p_fig = color_corr_bars(corr_p_fig, vector, color, options["opacity"])

        # Create scatter plot of vector vs parameter
        scatter_fig = ScatterPlot(
            merged_df,
            response=vector,
            param=parameter,
            color=color,
            title=f"{vector} vs {parameter}",
            plot_trendline=True,
        )
        scatter_fig.update_color(color, options["opacity"])

        # Make timeseries graph
        df_value_norm = parametermodel.get_real_and_value_df(
            ensemble, parameter=parameter, normalize=True
        )
        timeseries_fig = TimeSeriesFigure(
            dframe=merge_dataframes_on_realization(
                vector_df[["DATE", "REAL", vector]], df_value_norm
            ),
            visualization=visualization,
            vector=vector,
            ensemble=ensemble,
            dateline=date if options["show_dateline"] else None,
            historical_vector_df=vectormodel.get_historical_vector_df(vector, ensemble),
            color_col=parameter,
            line_shape_fallback=vectormodel.line_shape_fallback,
        ).figure

        return timeseries_fig, scatter_fig.figure, corr_v_fig, corr_p_fig

    @app.callback(
        Output(get_uuid("date-slider"), "value"),
        Input(get_uuid("vector-vs-time-graph"), "clickData"),
        State(get_uuid("date-selected"), "data"),
    )
    def _update_date_from_clickdata(timeseries_clickdata: Union[None, dict], date):
        """Update date-slider from clickdata"""
        date = (
            timeseries_clickdata.get("points", [{}])[0]["x"]
            if timeseries_clickdata is not None
            else date
        )
        return vectormodel.dates.index(datetime_utils.from_str(date))

    @app.callback(
        Output(get_uuid("vector-filter-store"), "data"),
        Output(get_uuid("submit-vector-filter"), "style"),
        Input(get_uuid("submit-vector-filter"), "n_clicks"),
        Input(get_uuid("vector-filter"), "value"),
        State(get_uuid("vector-filter-store"), "data"),
        State(get_uuid("submit-vector-filter"), "style"),
    )
    def _update_vector_filter_store_and_button_style(
        _n_click: int, vector_filter: str, stored: str, style: dict
    ):
        """Update vector-filter-store if submit button is clicked and
        style of submit button"""
        ctx = callback_context.triggered[0]["prop_id"]
        button_click = "submit" in ctx
        insync = stored == vector_filter
        style["background-color"] = "#E8E8E8" if insync or button_click else "#7393B3"
        style["color"] = "#555" if insync or button_click else "#fff"
        return vector_filter if button_click else no_update, style

    @app.callback(
        Output(get_uuid("date-selected"), "data"),
        Input(get_uuid("date-slider"), "value"),
    )
    def _update_date(dateidx: int):
        """Update selected date from date-slider"""
        return datetime_utils.to_str(vectormodel.dates[dateidx])

    @app.callback(
        Output(get_uuid("date-selected-text"), "children"),
        Input(get_uuid("date-slider"), "drag_value"),
        prevent_initial_call=True,
    )
    def _update_date(dateidx: int):
        """Update selected date text on date-slider drag"""
        return datetime_utils.to_str(vectormodel.dates[dateidx])

    @app.callback(
        Output({"id": get_uuid("plot-options"), "tab": "response"}, "data"),
        Input({"id": get_uuid("checkbox-options"), "tab": "response"}, "value"),
        Input({"id": get_uuid("color-selector"), "tab": "response"}, "clickData"),
        Input({"id": get_uuid("opacity-selector"), "tab": "response"}, "value"),
        State({"id": get_uuid("plot-options"), "tab": "response"}, "data"),
    )
    def _update_plot_options(
        checkbox_options: list,
        color_clickdata: str,
        opacity: float,
        plot_options: dict,
    ):
        """Combine plot options in one dictionary"""
        ctx = callback_context.triggered[0]["prop_id"].split(".")[0]
        if plot_options is not None and not ctx:
            raise PreventUpdate
        if color_clickdata is not None:
            color = color_clickdata["points"][0]["marker.color"]
            if "rgb" in color:
                color = rgba_to_hex(color)

        return dict(
            show_dateline="DateLine" in checkbox_options,
            autocompute_corr="AutoCompute" in checkbox_options,
            color=None if color_clickdata is None else color,
            opacity=opacity,
            ctx=ctx,
        )

    @app.callback(
        Output(get_uuid("vector-selector"), "selectedTags"),
        Input(get_uuid("param-corr-graph"), "clickData"),
    )
    def _update_vectorlist(corr_param_clickdata: dict):
        """Update the selected vector value from clickdata"""
        if corr_param_clickdata is None:
            raise PreventUpdate
        vector_selected = corr_param_clickdata.get("points", [{}])[0].get("y")
        return [vector_selected]

    @app.callback(
        Output({"id": get_uuid("parameter-select"), "tab": "response"}, "options"),
        Output({"id": get_uuid("parameter-select"), "tab": "response"}, "value"),
        Input(get_uuid("vector-corr-graph"), "clickData"),
        Input({"id": get_uuid("ensemble-selector"), "tab": "response"}, "value"),
        State({"id": get_uuid("parameter-select"), "tab": "response"}, "value"),
    )
    def _update_parameter_selected(
        corr_vector_clickdata: Union[None, dict], ensemble: str, selected_parameter: str
    ) -> tuple:
        """Update the selected parameter from clickdata, or when ensemble is changed"""
        ctx = callback_context.triggered[0]["prop_id"]
        if ctx == ".":
            raise PreventUpdate
        parameters = parametermodel.pmodel.parameters_per_ensemble[ensemble]
        options = [{"label": i, "value": i} for i in parameters]
        if "vector-corr-graph" in ctx:
            return options, corr_vector_clickdata.get("points", [{}])[0].get("y")
        return options, selected_parameter if selected_parameter in parameters else None

    @app.callback(
        Output({"id": get_uuid("parameter-filter"), "type": "ensemble-update"}, "data"),
        Input({"id": get_uuid("ensemble-selector"), "tab": "response"}, "value"),
    )
    def _update_parameter_filter_selection(ensemble: str):
        """Update ensemble in parameter filter"""
        return [ensemble]

    @app.callback(
        Output(get_uuid("param-filter-wrapper"), "style"),
        Input(get_uuid("display-paramfilter"), "n_clicks"),
        State(get_uuid("param-filter-wrapper"), "style"),
    )
    def _show_hide_parameter_filter(_n_click: list, style: dict):
        """Display/hide parameter filter"""
        if _n_click is None:
            raise PreventUpdate
        style.update(display="block" if style["display"] == "none" else "none")
        return style

    @app.callback(
        Output(get_uuid("options-dialog"), "open"),
        Input(get_uuid("options-button"), "n_clicks"),
        State(get_uuid("options-dialog"), "open"),
    )
    def open_close_options_dialog(_n_click: list, is_open: bool) -> bool:
        if _n_click is not None:
            return not is_open
        raise PreventUpdate


def make_correlation_figure(df: pd.DataFrame, response: str, corrwith: list):
    """Create a bar plot with correlations for chosen response"""
    corrseries = correlate_response_with_dataframe(df, response, corrwith)
    return BarChart(
        corrseries, n_rows=15, title=f"Correlations with {response}", orientation="h"
    )


def color_corr_bars(
    figure: dict,
    selected_bar: str,
    color: str,
    opacity: float,
    color_selected="#FF1243",
):
    """
    Set colors to the correlation plot bar,
    with separate color for the selected bar
    """
    if "data" in figure:
        figure["data"][0]["marker"] = {
            "color": [
                hex_to_rgba_str(color, opacity)
                if _bar != selected_bar
                else hex_to_rgba_str(color_selected, 0.8)
                for _bar in figure["data"][0]["y"]
            ],
            "line": {
                "color": [
                    color if _bar != selected_bar else color_selected
                    for _bar in figure["data"][0]["y"]
                ],
                "width": 1.2,
            },
        }
    return figure


def empty_figure(text="No data available for figure") -> go.Figure:
    return go.Figure(
        layout={
            "xaxis": {"visible": False},
            "yaxis": {"visible": False},
            "plot_bgcolor": "white",
            "annotations": [
                {
                    "text": text,
                    "xref": "paper",
                    "yref": "paper",
                    "showarrow": False,
                    "font": {"size": 16},
                }
            ],
        }
    )
