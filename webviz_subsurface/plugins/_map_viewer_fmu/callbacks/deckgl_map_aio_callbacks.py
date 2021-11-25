from typing import List, Callable, Optional
from flask import url_for
from dash import Input, Output, State, callback, callback_context, no_update

from webviz_subsurface._components import DeckGLMapAIO
from webviz_subsurface._components.deckgl_map.data_loaders import (
    surface_to_deckgl_spec,
    XtgeoWellsJson,
)

from webviz_config.utils._dash_component_utils import calculate_slider_step
from webviz_subsurface._models import WellSetModel

from ..models.surface_set_model import SurfaceContext, SurfaceSetModel
from ..layout.settings_view import ColorMapID
from ..layout.data_selector_view import SurfaceSelectorID, WellSelectorID


def deckgl_map_aio_callbacks(
    get_uuid: Callable,
    surface_set_models: List[SurfaceSetModel],
    well_set_model: Optional[WellSetModel] = None,
) -> None:
    @callback(
        Output(DeckGLMapAIO.ids.propertymap_image(get_uuid("mapview")), "data"),
        Output(DeckGLMapAIO.ids.propertymap_range(get_uuid("mapview")), "data"),
        Output(DeckGLMapAIO.ids.propertymap_bounds(get_uuid("mapview")), "data"),
        Input(get_uuid(SurfaceSelectorID.SELECTED_DATA.value), "data"),
    )
    def _update_property_map(surface_selected_data: str):
        selected_surface = SurfaceContext(**surface_selected_data)
        ensemble = selected_surface.ensemble
        surface = surface_set_models[ensemble].get_surface(selected_surface)
        spec = surface_to_deckgl_spec(surface)
        return (
            url_for("_send_surface_as_png", surface_context=selected_surface),
            spec["mapRange"],
            spec["mapBounds"],
        )

    @callback(
        Output(DeckGLMapAIO.ids.colormap_image(get_uuid("mapview")), "data"),
        Input(get_uuid(ColorMapID.SELECT.value), "value"),
    )
    def _update_color_map(colormap):
        return f"/colormaps/{colormap}.png"

    if well_set_model is not None:

        @callback(
            Output(DeckGLMapAIO.ids.well_data(get_uuid("mapview")), "data"),
            Input(get_uuid(WellSelectorID.WELLS), "value"),
        )
        def _update_well_data(wells):
            well_data = XtgeoWellsJson(
                wells=[well_set_model.get_well(well) for well in wells]
            )
            return well_data.feature_collection

    @callback(
        Output(DeckGLMapAIO.ids.colormap_range(get_uuid("mapview")), "data"),
        Input(get_uuid(ColorMapID.RANGE.value), "value"),
    )
    def _update_colormap_range(colormap_range):
        return colormap_range

    @callback(
        Output(get_uuid(ColorMapID.RANGE.value), "min"),
        Output(get_uuid(ColorMapID.RANGE.value), "max"),
        Output(get_uuid(ColorMapID.RANGE.value), "step"),
        Output(get_uuid(ColorMapID.RANGE.value), "value"),
        Output(get_uuid(ColorMapID.RANGE.value), "marks"),
        Input(DeckGLMapAIO.ids.propertymap_range(get_uuid("mapview")), "data"),
        Input(get_uuid(ColorMapID.KEEP_RANGE.value), "value"),
        Input(get_uuid(ColorMapID.RESET_RANGE.value), "n_clicks"),
        State(get_uuid(ColorMapID.RANGE.value), "value"),
    )
    def _update_colormap_range_slider(value_range, keep, reset, current_val):
        ctx = callback_context.triggered[0]["prop_id"]
        min_val = value_range[0]
        max_val = value_range[1]
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
