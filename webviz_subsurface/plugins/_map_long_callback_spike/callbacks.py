from enum import Enum
from dataclasses import dataclass
from dash import callback, Input, Output, State, ALL
from dash.exceptions import PreventUpdate
import webviz_core_components as wcc
from webviz_subsurface._providers.ensemble_surface_provider.ensemble_surface_provider import (
    SimulatedSurfaceAddress,
    StatisticalSurfaceAddress,
    ObservedSurfaceAddress,
    SurfaceAddress,
)
from .layout import surface_selectors, EnsembleSurfaceProviderContent


@dataclass
class SelectedSurfaceValues:
    ensemble: str = None
    attribute: str = None
    name: str = None
    date: str = None
    stype: str = None


@dataclass
class SurfaceType(str, Enum):
    REAL = "Single Realization"
    MEAN = "Mean"


def plugin_callbacks(get_uuid, ensemble_surface_providers, surface_server):
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
        Output(get_uuid("surface-selectors"), "children"),
        Input(get_uuid("stored-selections"), "data"),
    )
    def _store_selections(stored_selections):
        selected_surface = SelectedSurfaceValues(**stored_selections)
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
        return surface_selectors(get_uuid, surface_provider_content)

    @callback(
        Output(get_uuid("deckgl"), "data"),
        Input(get_uuid("stored-selections"), "data"),
        prevent_initial=True,
    )
    def _store_selections(stored_selections):
        print(stored_selections)
        selected_surface = SelectedSurfaceValues(**stored_selections)
        if selected_surface.ensemble is None:
            raise PreventUpdate
        surface_provider = ensemble_surface_providers[selected_surface.ensemble]
        if selected_surface.stype == SurfaceType.REAL:
            surface_address = SimulatedSurfaceAddress(
                attribute=selected_surface.attribute,
                name=selected_surface.name,
                datestr=selected_surface.date,
                realization=surface_provider.realizations()[0],
            )
        else:
            surface_address = StatisticalSurfaceAddress(
                attribute=selected_surface.attribute,
                name=selected_surface.name,
                datestr=selected_surface.date,
                realizations=surface_provider.realizations(),
                statistic="Mean",
            )
        raise PreventUpdate
