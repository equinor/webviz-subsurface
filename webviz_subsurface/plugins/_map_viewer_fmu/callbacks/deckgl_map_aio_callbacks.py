from typing import List, Callable, Optional, Dict
from flask import url_for
from dash import Input, Output, State, callback, callback_context, no_update, ALL

from webviz_subsurface._components import DeckGLMapAIO
from webviz_subsurface._components.deckgl_map.data_loaders import (
    surface_to_deckgl_spec,
    XtgeoWellsJson,
    DeckGLWellsContext,
)

from webviz_config.utils._dash_component_utils import calculate_slider_step
from webviz_subsurface._models import WellSetModel

from ..models.surface_set_model import SurfaceContext, SurfaceSetModel
from ..layout.settings_view import ColorMapID, ColorLinkID
from ..layout.data_selector_view import SurfaceSelectorID, WellSelectorID


def deckgl_map_aio_callbacks(
    get_uuid: Callable,
    surface_set_models: List[SurfaceSetModel],
    well_set_model: Optional[WellSetModel] = None,
) -> None:
    disabled_style = {"opacity": 0.5, "pointerEvents": "none"}

    @callback(
        Output(DeckGLMapAIO.ids.propertymap_image(get_uuid("mapview")), "data"),
        Output(DeckGLMapAIO.ids.propertymap_range(get_uuid("mapview")), "data"),
        Output(DeckGLMapAIO.ids.propertymap_bounds(get_uuid("mapview")), "data"),
        Input(
            {"id": get_uuid(SurfaceSelectorID.SELECTED_DATA), "view": "view1"}, "data"
        ),
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
        Input({"id": get_uuid(ColorMapID.SELECT), "view": "view1"}, "value"),
    )
    def _update_color_map(colormap):
        return f"/colormaps/{colormap}.png"

    if well_set_model is not None:

        @callback(
            Output(DeckGLMapAIO.ids.well_data(get_uuid("mapview")), "data"),
            Input(get_uuid(WellSelectorID.WELLS), "value"),
        )
        def _update_well_data(wells):
            wells_context = DeckGLWellsContext(well_names=wells)
            return url_for("_send_well_data_as_json", wells_context=wells_context)

    @callback(
        Output(DeckGLMapAIO.ids.colormap_range(get_uuid("mapview")), "data"),
        Input({"id": get_uuid(ColorMapID.RANGE), "view": "view1"}, "value"),
    )
    def _update_colormap_range(colormap_range):
        return colormap_range

    @callback(
        Output({"id": get_uuid(ColorMapID.RANGE), "view": "view1"}, "min"),
        Output({"id": get_uuid(ColorMapID.RANGE), "view": "view1"}, "max"),
        Output({"id": get_uuid(ColorMapID.RANGE), "view": "view1"}, "step"),
        Output({"id": get_uuid(ColorMapID.RANGE), "view": "view1"}, "value"),
        Output({"id": get_uuid(ColorMapID.RANGE), "view": "view1"}, "marks"),
        Input(DeckGLMapAIO.ids.propertymap_range(get_uuid("mapview")), "data"),
        Input({"id": get_uuid(ColorMapID.KEEP_RANGE), "view": "view1"}, "value"),
        Input({"id": get_uuid(ColorMapID.RESET_RANGE), "view": "view1"}, "n_clicks"),
        State({"id": get_uuid(ColorMapID.RANGE), "view": "view1"}, "value"),
    )
    def _update_colormap_range_slider(value_range, keep, reset, current_val):
        ctx = callback_context.triggered[0]["prop_id"]
        min_val = value_range[0]
        max_val = value_range[1]
        if ctx == ".":
            value = no_update
        if ColorMapID.RESET_RANGE in ctx or not keep or current_val is None:
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

    @callback(
        Output(DeckGLMapAIO.ids.propertymap_image(get_uuid("mapview2")), "data"),
        Output(DeckGLMapAIO.ids.propertymap_range(get_uuid("mapview2")), "data"),
        Output(DeckGLMapAIO.ids.propertymap_bounds(get_uuid("mapview2")), "data"),
        Input(
            {"id": get_uuid(SurfaceSelectorID.SELECTED_DATA), "view": "view2"}, "data"
        ),
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
        Output({"id": get_uuid(ColorMapID.RANGE), "view": "view2"}, "min"),
        Output({"id": get_uuid(ColorMapID.RANGE), "view": "view2"}, "max"),
        Output({"id": get_uuid(ColorMapID.RANGE), "view": "view2"}, "step"),
        Output({"id": get_uuid(ColorMapID.RANGE), "view": "view2"}, "value"),
        Output({"id": get_uuid(ColorMapID.RANGE), "view": "view2"}, "marks"),
        Output({"id": get_uuid(ColorMapID.RANGE), "view": "view2"}, "style"),
        Input(DeckGLMapAIO.ids.propertymap_range(get_uuid("mapview2")), "data"),
        Input({"id": get_uuid(ColorMapID.KEEP_RANGE), "view": "view2"}, "value"),
        Input({"id": get_uuid(ColorMapID.RESET_RANGE), "view": "view2"}, "n_clicks"),
        Input(get_uuid(ColorLinkID.RANGE), "value"),
        Input({"id": get_uuid(ColorMapID.RANGE), "view": "view1"}, "min"),
        Input({"id": get_uuid(ColorMapID.RANGE), "view": "view1"}, "max"),
        Input({"id": get_uuid(ColorMapID.RANGE), "view": "view1"}, "step"),
        Input({"id": get_uuid(ColorMapID.RANGE), "view": "view1"}, "value"),
        Input({"id": get_uuid(ColorMapID.RANGE), "view": "view1"}, "marks"),
        State({"id": get_uuid(ColorMapID.RANGE), "view": "view2"}, "value"),
    )
    def _update_colormap_range_slider(
        value_range,
        keep,
        reset,
        link: bool,
        view1_min: float,
        view1_max: float,
        view1_step: float,
        view1_value: float,
        view1_marks: Dict,
        current_val,
    ):
        ctx = callback_context.triggered[0]["prop_id"]
        min_val = value_range[0]
        max_val = value_range[1]
        if ctx == ".":
            value = no_update
        if link:
            return (
                view1_min,
                view1_max,
                view1_step,
                view1_value,
                view1_marks,
                disabled_style,
            )
        if ColorMapID.RESET_RANGE in ctx or not keep or current_val is None:
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
            {},
        )

    @callback(
        Output({"id": get_uuid(ColorMapID.KEEP_RANGE), "view": "view2"}, "style"),
        Output({"id": get_uuid(ColorMapID.RESET_RANGE), "view": "view2"}, "style"),
        Input(get_uuid(ColorLinkID.RANGE), "value"),
    )
    def _update_keep_range_style(link: bool):
        if link:
            return disabled_style, disabled_style
        return {}, {}

    @callback(
        Output(DeckGLMapAIO.ids.colormap_image(get_uuid("mapview2")), "data"),
        Input({"id": get_uuid(ColorMapID.SELECT), "view": "view2"}, "value"),
    )
    def _update_color_map(colormap):
        return f"/colormaps/{colormap}.png"

    @callback(
        Output(DeckGLMapAIO.ids.colormap_range(get_uuid("mapview2")), "data"),
        Input({"id": get_uuid(ColorMapID.RANGE), "view": "view2"}, "value"),
    )
    def _update_colormap_range(colormap_range):
        return colormap_range
