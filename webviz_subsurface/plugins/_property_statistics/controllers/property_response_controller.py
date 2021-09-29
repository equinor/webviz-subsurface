from typing import Callable, Tuple, Union

import numpy as np
import pandas as pd
from dash import ALL, Dash, Input, Output, State, callback_context, no_update
from dash.dash import _NoUpdate
from dash.exceptions import PreventUpdate

from webviz_subsurface._models import SurfaceLeafletModel

from ..figures.correlation_figure import CorrelationFigure
from ..models import PropertyStatisticsModel, SimulationTimeSeriesModel
from ..utils.colors import find_intermediate_color_rgba
from ..utils.surface import surface_from_zone_prop


def property_response_controller(
    get_uuid: Callable,
    surface_table: pd.DataFrame,
    property_model: PropertyStatisticsModel,
    timeseries_model: SimulationTimeSeriesModel,
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
        Input({"id": get_uuid("ensemble-selector"), "tab": "response"}, "value"),
        Input(get_uuid("property-response-vector-select"), "value"),
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
    ) -> Tuple[dict, dict]:
        if (
            callback_context.triggered is None
            or callback_context.triggered[0]["prop_id"] == "."
            or vector is None
        ):
            raise PreventUpdate
        ctx = callback_context.triggered[0]["prop_id"].split(".")[0]

        # Filter realizations if correlation filter is active
        real_filter = (
            property_model.filter_reals_on_label_range(ensemble, label, corr_filter)
            if corr_filter[0] is not None and corr_filter[1] is not None
            else None
        )

        # Make timeseries graph
        if any(
            substr in ctx
            for substr in [
                get_uuid("property-response-vector-select"),
                get_uuid("ensemble-selector"),
                get_uuid("property-response-correlated-slider"),
            ]
        ):

            figure = update_timeseries_graph(
                timeseries_model, ensemble, vector, real_filter
            )

        # Get clicked data or last available date initially
        date = (
            timeseries_clickdata.get("points", [{}])[0].get(
                "x", timeseries_model.get_last_date(ensemble)
            )
            if timeseries_clickdata
            else timeseries_model.get_last_date(ensemble)
        )

        # Draw clicked date as a black line
        ymin = min([min(trace["y"]) for trace in figure["data"]])
        ymax = max([max(trace["y"]) for trace in figure["data"]])
        figure["layout"]["shapes"] = [
            {"type": "line", "x0": date, "x1": date, "y0": ymin, "y1": ymax}
        ]

        # Get dataframe with vector and REAL
        vector_df = timeseries_model.get_ensemble_vector_for_date(
            ensemble=ensemble, vector=vector, date=date
        )
        vector_df["REAL"] = vector_df["REAL"].astype(int)

        # Get dataframe with properties per label and REAL
        prop_df = property_model.get_ensemble_properties(ensemble, selectors)
        prop_df["REAL"] = prop_df["REAL"].astype(int)
        prop_df = (
            prop_df[prop_df["REAL"].isin(real_filter)]
            if real_filter is not None
            else prop_df
        )

        # Correlate properties against vector
        corrseries = correlate(vector_df, prop_df, response=vector)
        # Make correlation figure
        correlation_figure = CorrelationFigure(corrseries, n_rows=20, title="")

        # Get clicked correlation bar or largest bar initially
        selected_corr = (
            correlation_clickdata.get("points", [{}])[0].get("y")
            if correlation_clickdata
            else correlation_figure.first_y_value
        )

        # Update bar colors
        correlation_figure.set_bar_colors(selected_corr)

        # Order realizations sorted on value of property
        real_order = (
            property_model.get_real_order(ensemble, series=selected_corr)
            if selected_corr is not None
            else None
        )

        # Color timeseries lines from value of property
        if real_order is not None:
            mean = real_order["Avg"].mean()
            low_reals = real_order[real_order["Avg"] <= mean]["REAL"].astype(str).values
            high_reals = real_order[real_order["Avg"] > mean]["REAL"].astype(str).values
            for trace_no, trace in enumerate(figure.get("data", [])):
                if trace["name"] == ensemble:
                    figure["data"][trace_no]["marker"]["color"] = set_real_color(
                        str(trace["customdata"]), low_reals, high_reals
                    )
            figure["layout"]["title"] = f"Colored by {selected_corr}"

        return figure, correlation_figure.figure


def set_real_color(real_no: str, low_reals: list, high_reals: list) -> str:

    if real_no in low_reals:
        index = int(list(low_reals).index(real_no))
        intermed = index / len(low_reals)
        return find_intermediate_color_rgba(
            "rgba(255,0,0, 100, .1)", "rgba(220,220,220, 0.1)", intermed
        )
    if real_no in high_reals:
        index = int(list(high_reals).index(real_no))
        intermed = index / len(high_reals)
        return find_intermediate_color_rgba(
            "rgba(220,220,220, 0.1)", "rgba(50,205,50, 1)", intermed
        )

    return "rgba(220,220,220, 0.2)"


def update_timeseries_graph(
    timeseries_model: SimulationTimeSeriesModel,
    ensemble: str,
    vector: str,
    real_filter: pd.Series = None,
) -> dict:

    return {
        "data": timeseries_model.add_realization_traces(
            ensemble=ensemble, vector=vector, real_filter=real_filter
        ),
        "layout": dict(
            margin={"r": 40, "l": 40, "t": 40, "b": 40},
        ),
    }


def correlate(vectordf: pd.DataFrame, propdf: pd.DataFrame, response: str) -> pd.Series:
    """Returns the correlation matrix for a dataframe"""
    df = pd.merge(propdf, vectordf, on=["REAL"])
    df = df[df.columns[df.nunique() > 1]]
    if response not in df.columns:
        df[response] = np.nan
    series = df[response]
    df = df.drop(columns=[response, "REAL"])
    corrdf = df.corrwith(series)
    return corrdf.reindex(corrdf.abs().sort_values().index)
