from dash.dependencies import Input, Output, ALL

from ..views.property_delta_view import table_view, surface_views
from ..utils.surface import surface_from_zone_prop
from ..models.surface_leaflet_model import (
    SurfaceLeafletModel,
)


def property_delta_controller(parent, app):
    @app.callback(
        Output(parent.uuid("delta-bar-graph"), "figure"),
        Output(parent.uuid("delta-table-surface-wrapper"), "children"),
        Input(parent.uuid("delta-switch-table-surface"), "value"),
        Input(parent.uuid("delta-sort"), "value"),
        Input({"id": parent.uuid("ensemble-selector"), "tab": "delta"}, "value"),
        Input({"id": parent.uuid("delta-ensemble-selector"), "tab": "delta"}, "value"),
        Input(
            {"id": parent.uuid("property-selector"), "tab": "delta"},
            "value",
        ),
        Input(
            {"id": parent.uuid("filter-selector"), "tab": "delta", "selector": ALL},
            "value",
        ),
        Input(parent.uuid("delta-bar-graph"), "clickData"),
    )
    def _update_bars(
        plot_type, sortby, ensemble, delta_ensemble, prop, selectors, clickdata
    ):
        # Make bar chart
        bars = parent.pmodel.make_delta_bars(
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
                parent=parent,
                prop=prop,
                zone=label.split(" | ")[0],
                ensemble=ensemble,
                delta_ensemble=delta_ensemble,
            )
        if plot_type == "table":
            columns, data = parent.pmodel.make_delta_table(
                prop=prop,
                ensemble=ensemble,
                delta_ensemble=delta_ensemble,
                selector_values=selectors,
                aggregation=sortby,
            )
            wrapper = table_view(data=data, columns=columns)

        return bars, wrapper


def make_surfaces(
    parent,
    prop: str,
    zone: str,
    ensemble: str,
    delta_ensemble: str,
    statistic: str = "mean",
):

    sprop = parent.surface_renaming.get(prop, prop)
    szone = parent.surface_renaming.get(zone, zone)
    ens_surface = surface_from_zone_prop(
        parent, zone=szone, prop=sprop, ensemble=ensemble, stype=statistic
    )
    delta_ens_surface = surface_from_zone_prop(
        parent, zone=szone, prop=sprop, ensemble=delta_ensemble, stype=statistic
    )

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
        parent=parent,
        prop=prop,
        zone=zone,
    )
