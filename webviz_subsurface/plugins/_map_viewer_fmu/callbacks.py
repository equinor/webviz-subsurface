from typing import Callable, Dict, List, Optional, Tuple, Any

from dash import Input, Output, State, callback, callback_context, no_update, ALL
from flask import url_for
import json

from webviz_config.utils._dash_component_utils import calculate_slider_step

from webviz_subsurface._components.deckgl_map.deckgl_map_layers_model import (
    DeckGLMapLayersModel,
)
from webviz_subsurface._components.deckgl_map.providers.xtgeo import (
    get_surface_bounds,
    get_surface_range,
)

from webviz_subsurface._models.well_set_model import WellSetModel

from .layout import (
    LayoutElements,
    SideBySideSelectorFlex,
    create_map_matrix,
    create_map_list,
)
from .providers.ensemble_surface_provider import SurfaceMode, EnsembleSurfaceProvider
from .types import SurfaceContext, WellsContext
from .utils.formatting import format_date  # , update_nested_dict


def plugin_callbacks(
    get_uuid: Callable,
    ensemble_surface_providers: Dict[str, EnsembleSurfaceProvider],
    well_set_model: Optional[WellSetModel],
) -> None:
    def selections() -> Dict[str, str]:
        return {
            "view": ALL,
            "id": get_uuid(LayoutElements.SELECTIONS),
            "selector": ALL,
        }

    def selector_wrapper() -> Dict[str, str]:
        return {"id": get_uuid(LayoutElements.WRAPPER), "selector": ALL}

    def links() -> Dict[str, str]:
        return {"id": get_uuid(LayoutElements.LINK), "selector": ALL}

    @callback(
        Output(get_uuid(LayoutElements.MAINVIEW), "children"),
        Input(get_uuid(LayoutElements.VIEWS), "value"),
    )
    def _update_number_of_maps(number_of_views) -> dict:
        return create_map_matrix(
            figures=create_map_list(
                get_uuid,
                views=number_of_views,
                well_set_model=well_set_model,
            )
        )

    @callback(
        Output(get_uuid(LayoutElements.RESET_BUTTOM_CLICK), "data"),
        Input(
            {"view": ALL, "id": get_uuid(LayoutElements.COLORMAP_RESET_RANGE)},
            "n_clicks",
        ),
        prevent_initial_call=True,
    )
    def _colormap_reset_indictor(_buttom_click) -> dict:
        ctx = callback_context.triggered[0]["prop_id"]
        update_view = json.loads(ctx.split(".")[0])["view"]
        return update_view if update_view is not None else no_update

    @callback(
        Output(get_uuid(LayoutElements.SELECTED_DATA), "data"),
        Output(selector_wrapper(), "children"),
        Output(get_uuid(LayoutElements.STORED_COLOR_SETTINGS), "data"),
        Input(selections(), "value"),
        Input(get_uuid(LayoutElements.WELLS), "value"),
        Input(links(), "value"),
        Input(get_uuid(LayoutElements.MAINVIEW), "children"),
        State(get_uuid(LayoutElements.VIEWS), "value"),
        Input(get_uuid(LayoutElements.RESET_BUTTOM_CLICK), "data"),
        State(selections(), "id"),
        State(selector_wrapper(), "id"),
        State(get_uuid(LayoutElements.SELECTED_DATA), "data"),
        State(links(), "id"),
        State(get_uuid(LayoutElements.STORED_COLOR_SETTINGS), "data"),
    )
    def _update_seleced_data_store(
        selector_values: list,
        selected_wells,
        link_values,
        _number_of_views_updated,
        number_of_views,
        color_reset_view,
        selector_ids,
        wrapper_ids,
        previous_selections,
        link_ids,
        stored_color_settings,
    ) -> Tuple[List[Dict], List[Any]]:
        ctx = callback_context.triggered[0]["prop_id"]

        links = {
            id_values["selector"]: bool(value)
            for value, id_values in zip(link_values, link_ids)
        }

        selections = []
        for idx in range(number_of_views):
            view_selections = {
                id_values["selector"]: {"value": values}
                for values, id_values in zip(selector_values, selector_ids)
                if id_values["view"] == idx
            }
            view_selections["wells"] = selected_wells
            view_selections["reset_colors"] = (
                get_uuid(LayoutElements.RESET_BUTTOM_CLICK) in ctx
                and color_reset_view == idx
            )
            view_selections["color_update"] = "color" in ctx
            view_selections["update"] = (
                previous_selections is None
                or get_uuid(LayoutElements.MAINVIEW) in ctx
                or get_uuid(LayoutElements.WELLS) in ctx
                or view_selections["reset_colors"]
                or f'"view":{idx}' in ctx
                or any(links.values())
            )
            selections.append(view_selections)

        for data in selections:
            for selector in links:
                if links[selector] and selector in data:
                    data[selector]["value"] = selections[0][selector]["value"]

        _update_ensemble_data(selections)
        _update_attribute_data(selections)
        _update_name_data(selections)
        _update_date_data(selections)
        _update_mode_data(selections)
        _update_realization_data(selections)
        stored_color_settings = _update_color_data(selections, stored_color_settings)

        return (
            selections,
            [
                SideBySideSelectorFlex(
                    get_uuid,
                    selector=id_val["selector"],
                    view_data=[data[id_val["selector"]] for data in selections],
                    link=links[id_val.get("selector", False)]
                    or len(selections[0][id_val["selector"]].get("options", [])) == 1,
                )
                for id_val in wrapper_ids
            ],
            stored_color_settings,
        )

    @callback(
        Output({"id": get_uuid(LayoutElements.DECKGLMAP), "view": ALL}, "layers"),
        Output({"id": get_uuid(LayoutElements.DECKGLMAP), "view": ALL}, "bounds"),
        Input(get_uuid(LayoutElements.SELECTED_DATA), "data"),
        State({"id": get_uuid(LayoutElements.DECKGLMAP), "view": ALL}, "layers"),
        State({"id": get_uuid(LayoutElements.DECKGLMAP), "view": ALL}, "id"),
    )
    def _update_maps(selections: dict, current_layers, map_ids):

        layers = []
        bounds = []
        for idx, map_id in enumerate(map_ids):
            data = selections[map_id["view"]]
            if data["update"]:
                selected_surface = get_surface_context_from_data(data)
                ensemble = selected_surface.ensemble
                surface = ensemble_surface_providers[ensemble].get_surface(
                    selected_surface
                )

                layer_model = DeckGLMapLayersModel(current_layers[idx])

                property_bounds = get_surface_bounds(surface)
                surface_range = get_surface_range(surface)
                layer_model.set_propertymap(
                    image_url=url_for(
                        "_send_surface_as_png", surface_context=selected_surface
                    ),
                    bounds=property_bounds,
                    value_range=surface_range,
                )
                layer_model.set_colormap_image(
                    f"/colormaps/{data['colormap']['value']}.png"
                )
                layer_model.set_colormap_range(data["color_range"]["value"])
                if well_set_model is not None:
                    layer_model.set_well_data(
                        well_data=url_for(
                            "_send_well_data_as_json",
                            wells_context=WellsContext(well_names=data["wells"]),
                        )
                    )
                layers.append(layer_model.layers)
                bounds.append(property_bounds)
            else:
                layers.append(no_update)
                bounds.append(no_update)

        return layers, bounds

    def _update_ensemble_data(selections) -> None:
        for data in selections:
            options = list(ensemble_surface_providers.keys())
            value = data["ensemble"]["value"] if "ensemble" in data else options[0]
            data["ensemble"] = {"value": value, "options": options}

    def _update_attribute_data(selections) -> None:
        for data in selections:
            options = ensemble_surface_providers.get(
                data["ensemble"]["value"]
            ).attributes

            value = (
                data["attribute"]["value"]
                if "attribute" in data and data["attribute"]["value"][0] in options
                else options[:1]
            )
            data["attribute"] = {"value": value, "options": options}

    def _update_name_data(selections) -> None:
        for data in selections:
            options = ensemble_surface_providers.get(
                data["ensemble"]["value"]
            ).names_in_attribute(data["attribute"]["value"][0])

            value = (
                data["name"]["value"]
                if "name" in data and data["name"]["value"][0] in options
                else options[:1]
            )
            data["name"] = {"value": value, "options": options}

    def _update_date_data(selections) -> None:
        for data in selections:
            options = ensemble_surface_providers.get(
                data["ensemble"]["value"]
            ).dates_in_attribute(data["attribute"]["value"][0])

            if not options:
                data["date"] = {"value": [], "options": []}
            else:
                value = (
                    data["date"]["value"]
                    if "date" in data
                    and data["date"]["value"]
                    and data["date"]["value"][0] in options
                    else options[:1]
                )
                data["date"] = {"value": value, "options": options}

    def _update_mode_data(selections) -> None:
        for data in selections:
            options = [mode for mode in SurfaceMode]
            value = data["mode"]["value"] if "mode" in data else SurfaceMode.REALIZATION
            data["mode"] = {"value": value, "options": options}

    def _update_realization_data(selections) -> None:
        for data in selections:
            options = ensemble_surface_providers[data["ensemble"]["value"]].realizations

            if SurfaceMode(data["mode"]["value"]) == SurfaceMode.REALIZATION:
                value = (
                    [data["realizations"]["value"][0]]
                    if "realizations" in data
                    else [options[0]]
                )
                multi = False
            else:
                value = (
                    data["realizations"]["value"]
                    if "realizations" in data and len(data["realizations"]["value"]) > 1
                    else options
                )
                multi = True

            data["realizations"] = {"value": value, "options": options, "multi": multi}

    def _update_color_data(selections, stored_color_settings) -> None:

        stored_color_settings = (
            stored_color_settings if stored_color_settings is not None else {}
        )

        colormaps = ["viridis_r", "seismic"]
        for data in selections:
            surfaceid = get_surface_id_from_data(data)

            selected_surface = get_surface_context_from_data(data)
            surface = ensemble_surface_providers[selected_surface.ensemble].get_surface(
                selected_surface
            )
            value_range = get_surface_range(surface)

            if (
                surfaceid in stored_color_settings
                and not data["reset_colors"]
                and not data["color_update"]
            ):
                colormap_value = stored_color_settings[surfaceid]["colormap"]
                color_range = stored_color_settings[surfaceid]["color_range"]
            else:
                colormap_value = (
                    data["colormap"]["value"] if "colormap" in data else colormaps[0]
                )
                color_range = (
                    value_range
                    if data["reset_colors"]
                    or (
                        not data["color_update"]
                        and not data.get("colormap_keep_range", {}).get("value")
                    )
                    else data["color_range"]["value"]
                )

            data["colormap"] = {"value": colormap_value, "options": colormaps}
            data["color_range"] = {
                "value": color_range,
                "step": calculate_slider_step(
                    min_value=value_range[0], max_value=value_range[1], steps=100
                )
                if value_range[0] != value_range[1]
                else 0,
                "range": value_range,
            }

            stored_color_settings[surfaceid] = {
                "colormap": colormap_value,
                "color_range": color_range,
            }

        return stored_color_settings

    def get_surface_context_from_data(data):
        return SurfaceContext(
            attribute=data["attribute"]["value"][0],
            name=data["name"]["value"][0],
            date=data["date"]["value"][0] if data["date"]["value"] else None,
            ensemble=data["ensemble"]["value"],
            realizations=data["realizations"]["value"],
            mode=data["mode"]["value"],
        )

    def get_surface_id_from_data(data):
        surfaceid = data["attribute"]["value"][0] + data["name"]["value"][0]
        if data["date"]["value"]:
            surfaceid += data["date"]["value"][0]
        return surfaceid
