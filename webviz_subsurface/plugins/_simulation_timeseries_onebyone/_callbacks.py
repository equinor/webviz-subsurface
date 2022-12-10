from typing import Callable, List, Union, Tuple

from dash import ALL, Input, Output, State, callback, ctx, html, no_update
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
from webviz_subsurface._utils.dataframe_utils import merge_dataframes_on_realization
from ._utils import datetime_utils
from ._layout import date_selector
from ._business_logic import SimulationTimeSeriesOneByOneDataModel


def plugin_callbacks(
    get_uuid: Callable, datamodel: SimulationTimeSeriesOneByOneDataModel
) -> None:
    @callback(
        Output(get_uuid("options-store"), "data"),
        Input({"id": get_uuid("options"), "selector": ALL}, "value"),
        State({"id": get_uuid("options"), "selector": ALL}, "id"),
    )
    def _update_options(option_values: list, options_id: List[dict]) -> dict:
        """Update graph with line coloring, vertical line and title"""
        return {opt["selector"]: value for opt, value in zip(options_id, option_values)}

    @callback(
        Output(get_uuid("real-store"), "data"),
        Input(get_uuid("sensitivity_filter"), "value"),
        State(get_uuid("ensemble"), "value"),
    )
    def _update_realization_store(sensitivites: list, ensemble: str) -> List[int]:
        """Update graph with line coloring, vertical line and title"""
        df = datamodel.get_sensitivity_dataframe_for_ensemble(ensemble)
        return list(df[df["SENSNAME"].isin(sensitivites)]["REAL"].unique())

    @callback(
        Output(get_uuid("sensitivity_filter"), "value"),
        Input(get_uuid("tornado-graph"), "clickData"),
        State({"id": get_uuid("options"), "selector": "Reference"}, "value"),
        prevent_initial_call=True,
    )
    def _update_sensitivity_filter(
        tornado_click_data: dict, reference: str
    ) -> List[str]:
        """Update graph with line coloring, vertical line and title"""
        clicked_data = tornado_click_data["points"][0]
        return [clicked_data["y"], reference]

    @callback(
        Output(get_uuid("sensitivity_filter"), "options"),
        Output({"id": get_uuid("options"), "selector": "Reference"}, "options"),
        Output({"id": get_uuid("options"), "selector": "Reference"}, "value"),
        Output(get_uuid("vector"), "data"),
        Output(get_uuid("vector"), "selectedTags"),
        Input(get_uuid("ensemble"), "value"),
        State(get_uuid("vector"), "selectedNodes"),
        State({"id": get_uuid("options"), "selector": "Reference"}, "value"),
    )
    def _update_sensitivity_filter_and_reference(
        ensemble: str, vector: list, reference: str
    ) -> tuple:
        """Update graph with line coloring, vertical line and title"""
        sensitivities = datamodel.get_unique_sensitivities_for_ensemble(ensemble)
        available_vectors = datamodel.vmodel._provider_set[
            ensemble
        ].vector_names_filtered_by_value(
            exclude_all_values_zero=True, exclude_constant_values=True
        )
        vector_selector_data = datamodel.vmodel.create_vector_selector_data(
            available_vectors
        )

        vector = vector if vector[0] in available_vectors else [available_vectors[0]]
        return (
            [{"label": elm, "value": elm} for elm in sensitivities],
            [{"label": elm, "value": elm} for elm in sensitivities],
            datamodel.get_tornado_reference(sensitivities, reference),
            vector_selector_data,
            vector,
        )

    @callback(
        Output(get_uuid("vector-store"), "data"),
        Input(get_uuid("vector"), "selectedNodes"),
    )
    def _update_vector_store(vector: list) -> str:
        """Unpack selected vector in vector selector"""
        if not vector:
            raise PreventUpdate
        return vector[0]

    @callback(
        Output(get_uuid("date-store"), "data"),
        Output(get_uuid("date_selector_wrapper"), "children"),
        Input(get_uuid("ensemble"), "value"),
        Input(get_uuid("graph"), "clickData"),
        Input({"id": get_uuid("date-slider"), "test": ALL}, "value"),
        State(get_uuid("date-store"), "data"),
    )
    def _render_date_selector(
        ensemble: str,
        timeseries_clickdata: Union[None, dict],
        dateidx: List[int],
        date: str,
    ) -> Tuple[str, html.Div]:
        """Store selected date and tornado input. Write statistics
        to table"""

        dates = datamodel.vmodel.dates_for_ensemble(ensemble)
        dateslider_drag = get_uuid("date-slider") in str(ctx.triggered_id)

        if timeseries_clickdata is not None and ctx.triggered_id == get_uuid("graph"):
            date = timeseries_clickdata.get("points", [{}])[0]["x"]
        elif dateslider_drag:
            date = datetime_utils.to_str(dates[dateidx[0]])

        date_selected = (
            datetime_utils.from_str(date)
            if datetime_utils.from_str(date) in dates
            else datamodel.vmodel.get_last_date(ensemble)
        )

        return (
            datetime_utils.to_str(date_selected),
            date_selector(get_uuid, date_selected=date_selected, dates=dates)
            if not dateslider_drag
            else no_update,
        )

    @callback(
        Output({"id": get_uuid("date-selected-text"), "test": ALL}, "children"),
        Input({"id": get_uuid("date-slider"), "test": ALL}, "drag_value"),
        Input(get_uuid("ensemble"), "value"),
        prevent_initial_call=True,
    )
    def _update_date_text(dateidx: List[int], ensemble: str) -> List[str]:
        """Update selected date text on date-slider drag"""
        if ctx.triggered_id == get_uuid("ensemble"):
            date = datamodel.vmodel.get_last_date(ensemble)
        else:
            dates = datamodel.vmodel.dates_for_ensemble(ensemble)
            date = dates[dateidx[0]]
        return [to_str(date)]

    @callback(
        Output(get_uuid("graph"), "figure"),
        Input(get_uuid("date-store"), "data"),
        Input(get_uuid("visualization"), "value"),
        Input(get_uuid("vector-store"), "data"),
        Input(get_uuid("real-store"), "data"),
        State(get_uuid("ensemble"), "value"),
    )
    def _update_timeseries_figure(
        date: str,
        visualization: str,
        vector: str,
        realizations: list,
        ensemble: str,
    ) -> go.Figure:
        # Get dataframe with vectors and dataframe with parameters and merge
        vector_df = datamodel.vmodel.get_vector_df(
            ensemble=ensemble, vectors=[vector], realizations=realizations
        )
        data = merge_dataframes_on_realization(
            dframe1=vector_df,
            dframe2=datamodel.get_sensitivity_dataframe_for_ensemble(ensemble),
        )
        if visualization == "sensmean":
            data = datamodel.create_vectors_statistics_df(data)

        return datamodel.create_timeseries_figure(
            data, vector, ensemble, date, visualization
        )

    @callback(
        Output(get_uuid("table"), "data"),
        Output(get_uuid("table"), "columns"),
        Output(get_uuid("tornado-graph"), "figure"),
        Input(get_uuid("date-store"), "data"),
        Input(get_uuid("options-store"), "data"),
        Input(get_uuid("vector-store"), "data"),
        State(get_uuid("ensemble"), "value"),
    )
    def _update_tornadoplot(
        date: str, selections: dict, vector: str, ensemble: str
    ) -> tuple:

        if selections is None or selections[
            "Reference"
        ] not in datamodel.get_unique_sensitivities_for_ensemble(ensemble):
            raise PreventUpdate

        # Get dataframe with vectors and dataframe with parameters and merge
        vector_df = datamodel.vmodel.get_vector_df(
            ensemble=ensemble, vectors=[vector], date=datetime_utils.from_str(date)
        )
        data = merge_dataframes_on_realization(
            dframe1=vector_df,
            dframe2=datamodel.get_sensitivity_dataframe_for_ensemble(ensemble),
        )

        tornado_data = datamodel.get_tornado_data(data, vector, selections)
        use_si_format = tornado_data.reference_average > 1000
        tornadofig = datamodel.create_tornado_figure(
            tornado_data, selections, use_si_format
        )
        table, columns = datamodel.create_tornado_table(tornado_data, use_si_format)
        return table, columns, tornadofig

    @callback(
        Output(get_uuid("real-graph"), "figure"),
        Input(get_uuid("date-store"), "data"),
        State(get_uuid("options-store"), "data"),
        Input(get_uuid("vector-store"), "data"),
        State(get_uuid("ensemble"), "value"),
        Input(get_uuid("bottom-viz"), "value"),
    )
    def _update_realplot(
        date: str,
        selections: dict,
        vector: str,
        ensemble: str,
        selected_vizualisation: str,
    ) -> go.Figure:
        if selections is None or selected_vizualisation == "table":
            raise PreventUpdate

        # Get dataframe with vectors and dataframe with parameters and merge
        vector_df = datamodel.vmodel.get_vector_df(
            ensemble=ensemble, vectors=[vector], date=datetime_utils.from_str(date)
        )
        data = merge_dataframes_on_realization(
            dframe1=vector_df,
            dframe2=datamodel.get_sensitivity_dataframe_for_ensemble(ensemble),
        )
        tornado_data = datamodel.get_tornado_data(data, vector, selections)

        return datamodel.create_realplot(tornado_data)

    @callback(
        Output(get_uuid("real-graph-wrapper"), "style"),
        Output(get_uuid("table-wrapper"), "style"),
        Input(get_uuid("bottom-viz"), "value"),
    )
    def _display_table_or_realplot(selected_vizualisation: str) -> tuple:
        return {"display": "none" if selected_vizualisation == "table" else "block"}, {
            "display": "block" if selected_vizualisation == "table" else "none"
        }
