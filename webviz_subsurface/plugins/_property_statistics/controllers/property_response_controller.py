from typing import Tuple, Union

import numpy as np
import pandas as pd
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate
import dash

from ..utils.colors import find_intermediate_color
from ..figures.correlation_figure import CorrelationFigure
from ..utils.surface import surface_from_zone_prop
from ..models.surface_leaflet_model import (
    SurfaceLeafletModel,
)


def property_response_controller(parent, app):
    @app.callback(
        Output({"id": parent.uuid("surface-view"), "tab": "response"}, "layers"),
        Output({"id": parent.uuid("surface-name"), "tab": "response"}, "children"),
        Input(parent.uuid("property-response-correlation-graph"), "clickData"),
        Input({"id": parent.uuid("ensemble-selector"), "tab": "response"}, "value"),
        Input({"id": parent.uuid("surface-type"), "tab": "response"}, "value"),
    )
    def _update_surface(
        clickdata: Union[None, dict], ensemble: str, stype: str
    ) -> Tuple[dict, str]:
        if clickdata is not None:
            label = clickdata["points"][0]["y"]
            prop = label.split(" | ")[0]
            zone = label.split(" | ")[1]
            sprop = parent.surface_renaming.get(prop, prop)
            szone = parent.surface_renaming.get(zone, zone)
            surface = surface_from_zone_prop(
                parent, zone=szone, prop=sprop, ensemble=ensemble, stype=stype
            )
            surface_layer = SurfaceLeafletModel(surface, name="surface").layer
            return [surface_layer], f"{stype.capitalize()} for {prop}, {zone}"
        raise PreventUpdate

    @app.callback(
        Output(parent.uuid("property-response-correlated-slider"), "min"),
        Output(parent.uuid("property-response-correlated-slider"), "max"),
        Output(parent.uuid("property-response-correlated-slider"), "step"),
        Output(parent.uuid("property-response-correlated-slider"), "value"),
        Output(parent.uuid("property-response-correlated-slider"), "marks"),
        Output(parent.uuid("property-response-correlated-slider"), "disabled"),
        Input(parent.uuid("property-response-correlated-filter"), "value"),
        Input({"id": parent.uuid("ensemble-selector"), "tab": "response"}, "value"),
    )
    # pylint: disable=protected-access
    def _update_correlation_figure(
        label: str, ensemble: str
    ) -> Tuple[
        Union[float, dash.dash._NoUpdate],
        Union[float, dash.dash._NoUpdate],
        Union[float, dash.dash._NoUpdate],
        list,
        Union[dict, dash.dash._NoUpdate],
        bool,
    ]:
        if label is not None:
            values = parent.pmodel.filter_on_label(label=label, ensemble=ensemble)
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
            dash.no_update,
            dash.no_update,
            dash.no_update,
            [None, None],
            dash.no_update,
            True,
        )

    @app.callback(
        Output(parent.uuid("property-response-vector-graph"), "figure"),
        Output(parent.uuid("property-response-correlation-graph"), "figure"),
        Input({"id": parent.uuid("ensemble-selector"), "tab": "response"}, "value"),
        Input(parent.uuid("property-response-vector-select"), "value"),
        Input(parent.uuid("property-response-vector-graph"), "clickData"),
        Input(parent.uuid("property-response-correlation-graph"), "clickData"),
        Input(
            {
                "id": parent.uuid("filter-selector"),
                "tab": "response",
                "selector": ALL,
            },
            "value",
        ),
        Input(parent.uuid("property-response-correlated-slider"), "value"),
        State(parent.uuid("property-response-vector-graph"), "figure"),
        State(parent.uuid("property-response-correlated-filter"), "value"),
    )
    # pylint: disable=too-many-locals
    def _update_graphs(
        ensemble: str,
        vector: str,
        timeseries_clickdata: Union[None, dict],
        correlation_clickdata: Union[None, dict],
        selectors: list,
        corr_filter: str,
        figure: dict,
        label: str,
    ) -> Tuple[dict, dict]:
        if (
            dash.callback_context.triggered is None
            or dash.callback_context.triggered[0]["prop_id"] == "."
            or vector is None
        ):
            raise PreventUpdate
        ctx = dash.callback_context.triggered[0]["prop_id"].split(".")[0]

        # Filter realizations if correlation filter is active
        real_filter = (
            parent.pmodel.filter_reals_on_label_range(ensemble, label, corr_filter)
            if corr_filter[0] is not None and corr_filter[1] is not None
            else None
        )

        # Make timeseries graph
        if any(
            substr in ctx
            for substr in [
                parent.uuid("property-response-vector-select"),
                parent.uuid("ensemble-selector"),
                parent.uuid("property-response-correlated-slider"),
            ]
        ):

            figure = update_timeseries_graph(
                parent.vmodel, ensemble, vector, real_filter
            )

        # Get clicked data or last available date initially
        date = (
            timeseries_clickdata.get("points", [{}])[0].get(
                "x", parent.vmodel.get_last_date(ensemble)
            )
            if timeseries_clickdata
            else parent.vmodel.get_last_date(ensemble)
        )

        # Draw clicked date as a black line
        ymin = min([min(trace["y"]) for trace in figure["data"]])
        ymax = max([max(trace["y"]) for trace in figure["data"]])
        figure["layout"]["shapes"] = [
            {"type": "line", "x0": date, "x1": date, "y0": ymin, "y1": ymax}
        ]

        # Get dataframe with vector and REAL
        vector_df = parent.vmodel.get_ensemble_vector_for_date(
            ensemble=ensemble, vector=vector, date=date
        )
        vector_df["REAL"] = vector_df["REAL"].astype(int)

        # Get dataframe with properties per label and REAL
        prop_df = parent.pmodel.get_ensemble_properties(ensemble, selectors)
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
            parent.pmodel.get_real_order(ensemble, series=selected_corr)
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


def set_real_color(real_no: str, low_reals: list, high_reals: list):

    if real_no in low_reals:
        index = int(list(low_reals).index(real_no))
        intermed = index / len(low_reals)
        return find_intermediate_color(
            "rgba(255,0,0, 100, .1)",
            "rgba(220,220,220, 0.1)",
            intermed,
            colortype="rgba",
        )
    if real_no in high_reals:
        index = int(list(high_reals).index(real_no))
        intermed = index / len(high_reals)
        return find_intermediate_color(
            "rgba(220,220,220, 0.1)", "rgba(50,205,50, 1)", intermed, colortype="rgba"
        )

    return "rgba(220,220,220, 0.2)"


def update_timeseries_graph(timeseries_model, ensemble, vector, real_filter=None):

    return {
        "data": timeseries_model.add_realization_traces(
            ensemble=ensemble, vector=vector, real_filter=real_filter
        ),
        "layout": dict(
            margin={"r": 40, "l": 40, "t": 40, "b": 40},
        ),
    }


def correlate(vectordf, propdf, response):
    """Returns the correlation matrix for a dataframe"""
    df = pd.merge(propdf, vectordf, on=["REAL"])
    df = df[df.columns[df.nunique() > 1]]
    if response not in df.columns:
        df[response] = np.nan
    series = df[response]
    df = df.drop(columns=[response, "REAL"])
    corrdf = df.corrwith(series)
    return corrdf.reindex(corrdf.abs().sort_values().index)
