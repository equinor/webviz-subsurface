from typing import Callable, Tuple, Union

import pandas as pd
from dash import ALL, Dash, Input, Output, State, callback_context, no_update
from dash.dash import _NoUpdate
from dash.exceptions import PreventUpdate

from webviz_subsurface._figures import BarChart, ScatterPlot, TimeSeriesFigure
from webviz_subsurface._models import SurfaceLeafletModel
from webviz_subsurface._utils.dataframe_utils import (
    correlate_response_with_dataframe,
    merge_dataframes_on_realization,
)
from webviz_subsurface.plugins._simulation_time_series.utils.datetime_utils import (
    from_str,
)

from ..models import (
    PropertyStatisticsModel,
    ProviderTimeSeriesDataModel,
    SimulationTimeSeriesModel,
)
from ..utils.surface import surface_from_zone_prop


def property_response_controller(
    get_uuid: Callable,
    surface_table: pd.DataFrame,
    property_model: PropertyStatisticsModel,
    timeseries_model: Union[SimulationTimeSeriesModel, ProviderTimeSeriesDataModel],
    app: Dash,
) -> None:
    @app.callback(
        Output({"id": get_uuid("surface-view"), "tab": "response"}, "layers"),
        Output({"id": get_uuid("surface-name"), "tab": "response"}, "children"),
        Input(get_uuid("property-response-correlation-graph"), "clickData"),
        Input({"id": get_uuid("ensemble-selector"), "tab": "response"}, "value"),
        Input({"id": get_uuid("surface-type"), "tab": "response"}, "value"),
    )
    def _update_surface(
        clickdata: Union[None, dict], ensemble: str, stype: str
    ) -> Tuple[list, str]:
        if clickdata is not None:
            label = clickdata["points"][0]["y"]
            prop = label.split(" | ")[0]
            zone = label.split(" | ")[1]

            try:
                surface = surface_from_zone_prop(
                    surface_table,
                    zone=zone,
                    prop=prop,
                    ensemble=ensemble,
                    stype=stype,
                )
            except ValueError:  # Surface does not exist
                return (
                    no_update,
                    f"No surface found for {stype.capitalize()} for {prop}, {zone}",
                )
            surface_layer = SurfaceLeafletModel(surface, name="surface").layer
            return [surface_layer], f"{stype.capitalize()} for {prop}, {zone}"
        raise PreventUpdate

    @app.callback(
        Output(get_uuid("property-response-correlated-slider"), "min"),
        Output(get_uuid("property-response-correlated-slider"), "max"),
        Output(get_uuid("property-response-correlated-slider"), "step"),
        Output(get_uuid("property-response-correlated-slider"), "value"),
        Output(get_uuid("property-response-correlated-slider"), "marks"),
        Output(get_uuid("property-response-correlated-slider"), "disabled"),
        Input(get_uuid("property-response-correlated-filter"), "value"),
        Input({"id": get_uuid("ensemble-selector"), "tab": "response"}, "value"),
    )
    def _update_correlation_figure(
        label: str, ensemble: str
    ) -> Tuple[
        Union[float, _NoUpdate],
        Union[float, _NoUpdate],
        Union[float, _NoUpdate],
        list,
        Union[dict, _NoUpdate],
        bool,
    ]:
        if label is not None:
            values = property_model.filter_on_label(label=label, ensemble=ensemble)
            return (
                values.min(),
                values.max(),
                (values.max() - values.min()) / 100,
                [values.min(), values.max()],
                {
                    str(values.min()): {"label": f"{values.min():.2f}"},
                    str(values.max()): {"label": f"{values.max():.2f}"},
                },
                False,
            )

        return (
            no_update,
            no_update,
            no_update,
            [None, None],
            no_update,
            True,
        )

    @app.callback(
        Output(get_uuid("property-response-vector-graph"), "figure"),
        Output(get_uuid("property-response-correlation-graph"), "figure"),
        Output(get_uuid("property-response-scatter-graph"), "figure"),
        Input({"id": get_uuid("ensemble-selector"), "tab": "response"}, "value"),
        Input(get_uuid("property-response-vector-select"), "selectedNodes"),
        Input(get_uuid("property-response-vector-graph"), "clickData"),
        Input(get_uuid("property-response-correlation-graph"), "clickData"),
        Input(
            {
                "id": get_uuid("filter-selector"),
                "tab": "response",
                "selector": ALL,
            },
            "value",
        ),
        Input(get_uuid("property-response-correlated-slider"), "value"),
        State(get_uuid("property-response-vector-graph"), "figure"),
        State(get_uuid("property-response-correlated-filter"), "value"),
    )
    # pylint: disable=too-many-locals
    def _update_graphs(
        ensemble: str,
        vector: str,
        timeseries_clickdata: Union[None, dict],
        correlation_clickdata: Union[None, dict],
        selectors: list,
        corr_filter: list,
        figure: dict,
        label: str,
    ) -> Tuple[dict, dict, dict]:

        if (
            callback_context.triggered is None
            or callback_context.triggered[0]["prop_id"] == "."
            or vector is None
            or not vector
            or not all(filt for filt in selectors)
        ):
            raise PreventUpdate

        vector = vector[0]

        # Filter realizations if correlation filter is active
        real_filter = (
            property_model.filter_reals_on_label_range(ensemble, label, corr_filter)
            if corr_filter[0] is not None and corr_filter[1] is not None
            else None
        )

        # Get clicked data or last available date initially
        date = (
            timeseries_clickdata.get("points", [{}])[0].get(
                "x", timeseries_model.get_last_date(ensemble)
            )
            if timeseries_clickdata
            else timeseries_model.get_last_date(ensemble)
        )
        date = from_str(date) if isinstance(date, str) else date

        # Get dataframe with vector and REAL
        vector_df = timeseries_model.get_vector_df(
            ensemble=ensemble, vectors=[vector], realizations=real_filter
        )
        if date not in vector_df["DATE"].values or vector not in vector_df:
            return {}, {}, {}

        # Get dataframe with properties per label and REAL
        prop_df = property_model.get_ensemble_properties(ensemble, selectors)
        prop_df = (
            prop_df[prop_df["REAL"].isin(real_filter)]
            if real_filter is not None
            else prop_df
        )

        merged_df = merge_dataframes_on_realization(
            dframe1=vector_df[vector_df["DATE"] == date], dframe2=prop_df
        )
        # Correlate properties against vector
        corrseries = correlate_response_with_dataframe(
            merged_df,
            response=vector,
            corrwith=[col for col in prop_df if col != "REAL"],
        )
        # Handle missing
        if corrseries.empty:
            return {}, {}, {}

        # Make correlation figure
        correlation_figure = BarChart(
            corrseries, n_rows=15, title=f"Correlations with {vector}", orientation="h"
        )

        # Get clicked correlation bar or largest bar initially
        selected_corr = (
            correlation_clickdata.get("points", [{}])[0].get("y")
            if correlation_clickdata
            else correlation_figure.first_y_value
        )

        # Update bar colors
        correlation_figure.color_bars(selected_corr, color="#007079", opacity=0.5)
        prop_df_norm = property_model.get_real_and_value_df(
            ensemble, series=selected_corr, normalize=True
        )
        figure = TimeSeriesFigure(
            dframe=merge_dataframes_on_realization(vector_df, prop_df_norm),
            visualization="realizations",
            vector=vector,
            ensemble=ensemble,
            dateline=date,
            historical_vector_df=timeseries_model.get_historical_vector_df(
                vector, ensemble
            ),
            color_col=selected_corr,
            line_shape_fallback=timeseries_model.line_shape_fallback,
        ).figure

        scatter_fig = (
            ScatterPlot(
                merged_df,
                response=vector,
                param=selected_corr,
                color="#007079",
                title=f"{vector} vs {selected_corr}",
                plot_trendline=True,
            ).figure
            if selected_corr in merged_df
            else {}
        )

        return figure, correlation_figure.figure, scatter_fig
