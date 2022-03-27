from typing import Callable, Tuple

import pandas as pd
import plotly.graph_objects as go
from dash import ALL, Dash, Input, Output, html
from dash.exceptions import PreventUpdate

from webviz_subsurface._models import SurfaceLeafletModel

from ..models import PropertyStatisticsModel
from ..utils.surface import surface_from_zone_prop
from ..views.property_delta_view import surface_views, table_view


def property_delta_controller(
    get_uuid: Callable,
    property_model: PropertyStatisticsModel,
    surface_table: pd.DataFrame,
    app: Dash,
) -> None:
    @app.callback(
        Output(get_uuid("delta-bar-graph"), "figure"),
        Output(get_uuid("delta-table-surface-wrapper"), "children"),
        Input(get_uuid("delta-switch-table-surface"), "value"),
        Input(get_uuid("delta-sort"), "value"),
        Input({"id": get_uuid("ensemble-selector"), "tab": "delta"}, "value"),
        Input({"id": get_uuid("delta-ensemble-selector"), "tab": "delta"}, "value"),
        Input(
            {"id": get_uuid("property-selector"), "tab": "delta"},
            "value",
        ),
        Input(
            {"id": get_uuid("filter-selector"), "tab": "delta", "selector": ALL},
            "value",
        ),
        Input(get_uuid("delta-bar-graph"), "clickData"),
    )
    def _update_bars(
        plot_type: str,
        sortby: str,
        ensemble: str,
        delta_ensemble: str,
        prop: str,
        selectors: list,
        clickdata: dict,
    ) -> Tuple[go.Figure, html.Div]:
        # Prevent update if some filters are empty
        if not all(filt for filt in selectors):
            raise PreventUpdate

        # Make bar chart
        bars = property_model.make_delta_bars(
            prop=prop,
            ensemble=ensemble,
            delta_ensemble=delta_ensemble,
            selector_values=selectors,
            aggregation=sortby,
        )

        if plot_type == "surface":
            # Get selected bar or get highest delta bar if none is selected
            label = (
                clickdata["points"][0]["y"]
                if clickdata is not None
                else bars["data"][0]["y"][-1]
            )
            # Make surface div
            wrapper = make_surfaces(
                get_uuid=get_uuid,
                surface_table=surface_table,
                prop=prop,
                zone=label.split(" | ")[0],
                ensemble=ensemble,
                delta_ensemble=delta_ensemble,
            )
        if plot_type == "table":
            columns, data = property_model.make_delta_table(
                prop=prop,
                ensemble=ensemble,
                delta_ensemble=delta_ensemble,
                selector_values=selectors,
                aggregation=sortby,
            )
            wrapper = table_view(data=data, columns=columns)

        return bars, wrapper


def make_surfaces(
    surface_table: pd.DataFrame,
    prop: str,
    zone: str,
    ensemble: str,
    delta_ensemble: str,
    get_uuid: Callable,
    statistic: str = "mean",
) -> html.Div:

    try:
        ens_surface = surface_from_zone_prop(
            surface_table,
            zone=zone,
            prop=prop,
            ensemble=ensemble,
            stype=statistic,
        )
        delta_ens_surface = surface_from_zone_prop(
            surface_table,
            zone=zone,
            prop=prop,
            ensemble=delta_ensemble,
            stype=statistic,
        )
    except ValueError:
        return html.Div("No surfaces found")

    # Truncating surface values to highest low and lowest high for each map
    min_val = max([ens_surface.values.min(), delta_ens_surface.values.min()])
    max_val = min([ens_surface.values.max(), delta_ens_surface.values.max()])

    ens_surface.values[ens_surface.values < min_val] = min_val
    ens_surface.values[ens_surface.values > max_val] = max_val
    delta_ens_surface.values[delta_ens_surface.values < min_val] = min_val
    delta_ens_surface.values[delta_ens_surface.values > max_val] = max_val
    diff_surface = ens_surface.copy()
    diff_surface.values = ens_surface.values - delta_ens_surface.values
    return surface_views(
        ens_layer=SurfaceLeafletModel(ens_surface, name="ens_surface").layer,
        delta_ens_layer=SurfaceLeafletModel(
            delta_ens_surface, name="delta_ens_surface"
        ).layer,
        diff_layer=SurfaceLeafletModel(diff_surface, name="diff_surface").layer,
        ensemble=ensemble,
        delta_ensemble=delta_ensemble,
        get_uuid=get_uuid,
        prop=prop,
        zone=zone,
    )
