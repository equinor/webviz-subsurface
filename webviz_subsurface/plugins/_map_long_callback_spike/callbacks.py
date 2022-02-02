from enum import Enum
from dataclasses import dataclass
from dash import callback, Input, Output, State, ALL
from dash.long_callback import DiskcacheLongCallbackManager
from dash.exceptions import PreventUpdate
import dash
import webviz_core_components as wcc
from webviz_subsurface._providers.ensemble_surface_provider.ensemble_surface_provider import (
    SimulatedSurfaceAddress,
    StatisticalSurfaceAddress,
    ObservedSurfaceAddress,
    SurfaceAddress,
)
from webviz_subsurface._components.deckgl_map.types.deckgl_props import (
    ColormapLayer,
    Hillshading2DLayer,
)
from webviz_subsurface._providers.ensemble_surface_provider.surface_server import (
    QualifiedAddress,
    SurfaceMeta,
)
from .layout import surface_selectors, EnsembleSurfaceProviderContent

import diskcache

from dacite import from_dict
from dataclasses import asdict


@dataclass
class SelectedSurfaceAddress:
    ensemble: str = None
    attribute: str = None
    name: str = None
    date: str = None
    stype: str = None


@dataclass
class SurfaceType(str, Enum):
    REAL = "Single Realization"
    MEAN = "Mean"


def plugin_callbacks(app, get_uuid, ensemble_surface_providers, surface_server):
    cache = diskcache.Cache("./cache")
    long_callback_manager = DiskcacheLongCallbackManager(cache)

    @callback(
        Output(get_uuid("stored-selections"), "data"),
        Input({"id": get_uuid("selector"), "component": ALL}, "value"),
        State({"id": get_uuid("selector"), "component": ALL}, "id"),
    )
    def _store_selections(selection_values, selection_ids):
        return {
            selection_id["component"]: selection_value[0]
            if isinstance(selection_value, list)
            else selection_value
            for selection_value, selection_id in zip(selection_values, selection_ids)
        }

    @callback(
        Output(get_uuid("stored-surface-address"), "data"),
        Output(get_uuid("surface-selectors"), "children"),
        Input(get_uuid("stored-selections"), "data"),
    )
    def _store_selections(stored_selections):
        selected_surface = SelectedSurfaceAddress(**stored_selections)
        if selected_surface.ensemble == None:
            selected_surface.ensemble = list(ensemble_surface_providers.keys())[0]

        surface_provider = ensemble_surface_providers[selected_surface.ensemble]
        if selected_surface.attribute == None:
            selected_surface.attribute = surface_provider.attributes()[0]
        available_names = surface_provider.surface_names_for_attribute(
            selected_surface.attribute
        )
        if (
            selected_surface.name == None
            or selected_surface.name not in available_names
        ):
            selected_surface.name = available_names[0]

        available_dates = surface_provider.surface_dates_for_attribute(
            selected_surface.attribute
        )
        if (
            selected_surface.date == None
            or selected_surface.date not in available_dates
        ):
            selected_surface.date = next(iter(available_dates), None)

        if selected_surface.stype == None:
            selected_surface.stype = SurfaceType.REAL
        surface_provider_content = EnsembleSurfaceProviderContent(
            ensembles=list(ensemble_surface_providers.keys()),
            selected_ensemble=selected_surface.ensemble,
            attributes=surface_provider.attributes(),
            selected_attribute=selected_surface.attribute,
            names=available_names,
            selected_name=selected_surface.name,
            dates=available_dates,
            selected_date=selected_surface.date,
            stypes=SurfaceType,
            selected_type=selected_surface.stype,
        )
        return (selected_surface, surface_selectors(get_uuid, surface_provider_content))

    @app.long_callback(
        Output(get_uuid("stored-surface-meta"), "data"),
        Output(get_uuid("stored-qualified-address"), "data"),
        Input(get_uuid("stored-surface-address"), "data"),
        # progress=Output(get_uuid("value-range"), "children"),
        manager=long_callback_manager,
    )
    def _store_selections(selected_surface):

        if selected_surface is None:
            return dash.no_update, dash.no_update

        selected_surface = SelectedSurfaceAddress(**selected_surface)
        surface_provider = ensemble_surface_providers[selected_surface.ensemble]
        if selected_surface.stype == SurfaceType.REAL:
            surface_address = SimulatedSurfaceAddress(
                attribute=selected_surface.attribute,
                name=selected_surface.name,
                datestr=selected_surface.date if selected_surface.date else None,
                realization=int(
                    surface_provider.realizations()[0]
                ),  # TypeError: Object of type int64 is not JSON serializable
            )
        else:
            surface_address = StatisticalSurfaceAddress(
                attribute=selected_surface.attribute,
                name=selected_surface.name,
                datestr=selected_surface.date,
                realizations=[int(real) for real in surface_provider.realizations()],
                statistic="Mean",
            )

        qualified_address = QualifiedAddress(
            provider_id=surface_provider.provider_id(), address=surface_address
        )
        surf_meta = surface_server.get_surface_metadata(qualified_address)
        if not surf_meta:
            # This means we need to compute the surface
            surface = surface_provider.get_surface(address=surface_address)
            if not surface:
                raise ValueError(
                    f"Could not get surface for address: {surface_address}"
                )
            surface_server.publish_surface(qualified_address, surface)
            surf_meta = surface_server.get_surface_metadata(qualified_address)

        return surf_meta, qualified_address

    @callback(
        Output(get_uuid("value-range"), "children"),
        Input(get_uuid("stored-surface-meta"), "data"),
    )
    def _update_value_range(meta):
        if meta is None:
            raise PreventUpdate
        meta = SurfaceMeta(**meta)
        return [f"{'min'}:{meta.val_min},'\nmax': {meta.val_max}"]

    @callback(
        Output(get_uuid("deckgl"), "layers"),
        Output(get_uuid("deckgl"), "bounds"),
        Input(get_uuid("stored-surface-meta"), "data"),
        Input(get_uuid("stored-qualified-address"), "data"),
    )
    def _update_deckgl(meta, qualified_address_data):
        if meta is None or qualified_address_data is None:
            raise PreventUpdate
        meta = SurfaceMeta(**meta)

        #!! This is not a valid qualified address as nested dataclasses are not picked up.
        qualified_address = from_dict(
            data_class=QualifiedAddress, data=qualified_address_data
        )

        # print(asdict(qualified_address))
        # assert isinstance(qualified_address, QualifiedAddress)

        image = surface_server.encode_partial_url(qualified_address)

        viewport_bounds = [meta.x_min, meta.y_min, meta.x_max, meta.y_max]

        return [
            {
                "@@type": "Hillshading2DLayer",
                "image": image,
                "bounds": meta.deckgl_bounds,
                "valueRange": [meta.val_min, meta.val_max],
            },
        ], viewport_bounds
