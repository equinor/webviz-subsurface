from typing import List, Callable
from dash import Input, Output, State, callback, callback_context, no_update

from webviz_subsurface._components import DeckGLMapAIO
from webviz_config.utils._dash_component_utils import calculate_slider_step
from webviz_subsurface._models import SurfaceSetModel
from ..classes.surface_context import SurfaceContext
from ..layout.surface_settings_view import ColorMapID
from ..layout.surface_selector_view import SurfaceSelectorID


def deckgl_map_aio_callbacks(
    get_uuid: Callable, surface_set_models: List[SurfaceSetModel]
) -> None:
    @callback(
        Output(DeckGLMapAIO.ids.map_data(get_uuid("mapview")), "data"),
        Input(get_uuid(SurfaceSelectorID.SELECTED_DATA.value), "data"),
    )
    def _set_stored_surface_geometry(surface_selected_data: str):
        selected_surface = SurfaceContext(**surface_selected_data)
        ensemble = selected_surface.ensemble
        return surface_set_models[ensemble]._get_surface_deckgl_spec(selected_surface)

    @callback(
        Output(DeckGLMapAIO.ids.colormap_image(get_uuid("mapview")), "data"),
        Input(get_uuid(ColorMapID.SELECT.value), "value"),
    )
    def _set_color_map_image(colormap):
        return colormap

    @callback(
        Output(DeckGLMapAIO.ids.colormap_range(get_uuid("mapview")), "data"),
        Input(get_uuid(ColorMapID.RANGE.value), "value"),
    )
    def _set_color_map_range(colormap_range):
        return colormap_range

    @callback(
        Output(get_uuid(ColorMapID.RANGE.value), "min"),
        Output(get_uuid(ColorMapID.RANGE.value), "max"),
        Output(get_uuid(ColorMapID.RANGE.value), "step"),
        Output(get_uuid(ColorMapID.RANGE.value), "value"),
        Output(get_uuid(ColorMapID.RANGE.value), "marks"),
        Input(DeckGLMapAIO.ids.map_data(get_uuid("mapview")), "data"),
        Input(get_uuid(ColorMapID.KEEP_RANGE.value), "value"),
        Input(get_uuid(ColorMapID.RESET_RANGE.value), "n_clicks"),
        State(get_uuid(ColorMapID.RANGE.value), "value"),
    )
    def _set_colormap_range(surface_geometry, keep, reset, current_val):
        ctx = callback_context.triggered[0]["prop_id"]
        min_val = surface_geometry["mapRange"][0]
        max_val = surface_geometry["mapRange"][1]
        if ctx == ".":
            value = no_update
        if ColorMapID.RESET_RANGE.value in ctx or not keep or current_val is None:
            value = [min_val, max_val]
        else:
            value = current_val
        return (
            min_val,
            max_val,
            calculate_slider_step(min_value=min_val, max_value=max_val, steps=100)
            if min_val != max_val
            else 0,
            value,
            {
                str(min_val): {"label": f"{min_val:.2f}"},
                str(max_val): {"label": f"{max_val:.2f}"},
            },
        )
