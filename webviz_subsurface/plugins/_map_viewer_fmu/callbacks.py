from typing import Callable, Dict, List, Optional, Tuple, Any
import json
import math
from dash import Input, Output, State, callback, callback_context, no_update, ALL, MATCH
from dash.exceptions import PreventUpdate
from flask import url_for

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
    update_map_layers,
    DefaultSettings,
)
from .providers.ensemble_surface_provider import SurfaceMode, EnsembleSurfaceProvider
from .types import SurfaceContext, WellsContext
from .utils.formatting import format_date  # , update_nested_dict


def plugin_callbacks(
    get_uuid: Callable,
    ensemble_surface_providers: Dict[str, EnsembleSurfaceProvider],
    well_set_model: Optional[WellSetModel],
) -> None:
    def selections(tab) -> Dict[str, str]:
        return {
            "view": ALL,
            "id": get_uuid(LayoutElements.SELECTIONS),
            "tab": tab,
            "selector": ALL,
        }

    def selector_wrapper(tab) -> Dict[str, str]:
        return {
            "id": get_uuid(LayoutElements.WRAPPER),
            "tab": tab,
            "selector": ALL,
        }

    def links(tab) -> Dict[str, str]:
        return {"id": get_uuid(LayoutElements.LINK), "tab": tab, "selector": ALL}

    @callback(
        Output({"id": get_uuid(LayoutElements.SELECTED_DATA), "tab": MATCH}, "data"),
        Output(selector_wrapper(MATCH), "children"),
        Output(
            {"id": get_uuid(LayoutElements.STORED_COLOR_SETTINGS), "tab": MATCH},
            "data",
        ),
        Input({"id": get_uuid(LayoutElements.TEST), "tab": MATCH}, "data"),
        State({"id": get_uuid(LayoutElements.VIEWS), "tab": MATCH}, "value"),
        State(selector_wrapper(MATCH), "id"),
        State(
            {"id": get_uuid(LayoutElements.STORED_COLOR_SETTINGS), "tab": MATCH},
            "data",
        ),
        State(get_uuid("tabs"), "value"),
    )
    def _update_components_and_selected_data(
        test, number_of_views, wrapper_ids, stored_color_settings, tab
    ):
        selections, links = test
        if "mode" in DefaultSettings.SELECTOR_DEFAULTS.get(tab, {}):
            for idx in range(number_of_views):
                selections[idx]["mode"] = {
                    "value": DefaultSettings.SELECTOR_DEFAULTS[tab]["mode"][idx]
                }

        _update_ensemble_data(selections, links)
        _update_attribute_data(selections, links)
        _update_name_data(selections, links)
        _update_date_data(selections, links)
        _update_mode_data(selections, links)
        _update_realization_data(selections, links)
        stored_color_settings = _update_color_data(
            selections, stored_color_settings, links
        )

        return (
            selections,
            [
                SideBySideSelectorFlex(
                    tab,
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
        Output({"id": get_uuid(LayoutElements.TEST), "tab": MATCH}, "data"),
        Input(selections(MATCH), "value"),
        Input({"id": get_uuid(LayoutElements.WELLS), "tab": MATCH}, "value"),
        Input(links(MATCH), "value"),
        Input({"id": get_uuid(LayoutElements.VIEWS), "tab": MATCH}, "value"),
        Input(
            {"id": get_uuid(LayoutElements.RESET_BUTTOM_CLICK), "tab": MATCH},
            "data",
        ),
        Input(get_uuid("tabs"), "value"),
        State(selections(MATCH), "id"),
        State(links(MATCH), "id"),
        State({"id": get_uuid(LayoutElements.TEST), "tab": MATCH}, "data"),
    )
    def collect_selection_and_links(
        selector_values: list,
        selected_wells,
        link_values,
        number_of_views,
        color_reset_view,
        tab,
        selector_ids,
        link_ids,
        prev_selections,
    ):
        ctx = callback_context.triggered[0]["prop_id"]

        tab_clicked = link_ids[0]["tab"]
        if tab_clicked != tab or number_of_views is None:
            raise PreventUpdate

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
            selections.append(view_selections)

        if (
            prev_selections is not None
            and (prev_selections[0] == selections)
            and (prev_selections[1] == links)
        ):
            raise PreventUpdate

        return [selections, links]

    @callback(
        Output(
            {"id": get_uuid(LayoutElements.RESET_BUTTOM_CLICK), "tab": MATCH}, "data"
        ),
        Input(
            {
                "view": ALL,
                "id": get_uuid(LayoutElements.COLORMAP_RESET_RANGE),
                "tab": MATCH,
            },
            "n_clicks",
        ),
    )
    def _colormap_reset_indicator(_buttom_click) -> dict:
        ctx = callback_context.triggered[0]["prop_id"]
        if ctx == ".":
            raise PreventUpdate
        update_view = json.loads(ctx.split(".")[0])["view"]
        return update_view if update_view is not None else no_update

    @callback(
        Output({"id": get_uuid(LayoutElements.DECKGLMAP), "tab": MATCH}, "layers"),
        Output({"id": get_uuid(LayoutElements.DECKGLMAP), "tab": MATCH}, "bounds"),
        Output({"id": get_uuid(LayoutElements.DECKGLMAP), "tab": MATCH}, "views"),
        Input({"id": get_uuid(LayoutElements.SELECTED_DATA), "tab": MATCH}, "data"),
        Input({"id": get_uuid(LayoutElements.VIEW_COLUMNS), "tab": MATCH}, "value"),
        State({"id": get_uuid(LayoutElements.VIEWS), "tab": MATCH}, "value"),
        State({"id": get_uuid(LayoutElements.DECKGLMAP), "tab": MATCH}, "layers"),
    )
    def _update_map(selections: dict, view_columns, number_of_views, current_layers):
        if selections is None:
            raise PreventUpdate
        # layers = update_map_layers(number_of_views, well_set_model)
        # layers = [json.loads(x.to_json()) for x in layers]
        layer_model = DeckGLMapLayersModel(current_layers)

        for idx, data in enumerate(selections):
            selected_surface = get_surface_context_from_data(data)

            ensemble = selected_surface.ensemble
            surface = ensemble_surface_providers[ensemble].get_surface(selected_surface)
            surface_range = get_surface_range(surface)
            if idx == 0:
                property_bounds = get_surface_bounds(surface)

            layer_data = {
                "image": url_for(
                    "_send_surface_as_png", surface_context=selected_surface
                ),
                "bounds": property_bounds,
                "valueRange": surface_range,
            }

            layer_model.update_layer_by_id(
                layer_id=f"{LayoutElements.COLORMAP_LAYER}-{idx}", layer_data=layer_data
            )
            layer_model.update_layer_by_id(
                layer_id=f"{LayoutElements.HILLSHADING_LAYER}-{idx}",
                layer_data=layer_data,
            )
            layer_model.update_layer_by_id(
                layer_id=f"{LayoutElements.COLORMAP_LAYER}-{idx}",
                layer_data={
                    "colorMapName": data["colormap"]["value"],
                    "colorMapRange": data["color_range"]["value"],
                },
            )
            if well_set_model is not None:
                layer_model.update_layer_by_id(
                    layer_id=f"{LayoutElements.WELLS_LAYER}-{idx}",
                    layer_data={
                        "data": url_for(
                            "_send_well_data_as_json",
                            wells_context=WellsContext(well_names=data["wells"]),
                        )
                    },
                )

        return (
            layer_model.layers,
            property_bounds,
            {
                "layout": view_layout(number_of_views, view_columns),
                "viewports": [
                    {
                        "id": f"view_{view}",
                        "show3D": False,
                        "layerIds": [
                            f"{LayoutElements.COLORMAP_LAYER}-{view}",
                            f"{LayoutElements.HILLSHADING_LAYER}-{view}",
                            f"{LayoutElements.WELLS_LAYER}-{view}",
                        ],
                    }
                    for view in range(number_of_views)
                ],
            },
        )

    def _update_ensemble_data(selections, links) -> None:
        for idx, data in enumerate(selections):
            if not (links["ensemble"] and idx > 0):
                options = list(ensemble_surface_providers.keys())
                value = data["ensemble"]["value"] if "ensemble" in data else options[0]
            data["ensemble"] = {"value": value, "options": options}

    def _update_attribute_data(selections, links) -> None:
        for idx, data in enumerate(selections):
            if not (links["attribute"] and idx > 0):
                options = ensemble_surface_providers.get(
                    data["ensemble"]["value"]
                ).attributes

                value = (
                    data["attribute"]["value"]
                    if "attribute" in data and data["attribute"]["value"][0] in options
                    else options[:1]
                )
            data["attribute"] = {"value": value, "options": options}

    def _update_name_data(selections, links) -> None:
        for idx, data in enumerate(selections):
            if not (links["name"] and idx > 0):
                options = ensemble_surface_providers.get(
                    data["ensemble"]["value"]
                ).names_in_attribute(data["attribute"]["value"][0])

                value = (
                    data["name"]["value"]
                    if "name" in data and data["name"]["value"][0] in options
                    else options[:1]
                )
            data["name"] = {"value": value, "options": options}

    def _update_date_data(selections, links) -> None:
        for idx, data in enumerate(selections):
            if not (links["date"] and idx > 0):
                options = ensemble_surface_providers.get(
                    data["ensemble"]["value"]
                ).dates_in_attribute(data["attribute"]["value"][0])

                if options is None:
                    options = value = []
                else:
                    value = (
                        data["date"]["value"]
                        if "date" in data
                        and data["date"]["value"]
                        and data["date"]["value"][0] in options
                        else options[:1]
                    )
            data["date"] = {"value": value, "options": options}

    def _update_mode_data(selections, links) -> None:
        if "mode" not in links:
            return
        for idx, data in enumerate(selections):
            if not (links["mode"] and idx > 0):
                options = [mode for mode in SurfaceMode]
                value = (
                    data["mode"]["value"] if "mode" in data else SurfaceMode.REALIZATION
                )
            data["mode"] = {"value": value, "options": options}

    def _update_realization_data(selections, links) -> None:
        for idx, data in enumerate(selections):
            if not (links["realizations"] and idx > 0):
                options = ensemble_surface_providers[
                    data["ensemble"]["value"]
                ].realizations

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
                        if "realizations" in data
                        and len(data["realizations"]["value"]) > 1
                        else options
                    )
                    multi = True

            data["realizations"] = {"value": value, "options": options, "multi": multi}

    def _update_color_data(selections, stored_color_settings, links) -> None:

        stored_color_settings = (
            stored_color_settings if stored_color_settings is not None else {}
        )

        colormaps = [
            "Physics",
            "Rainbow",
            "Porosity",
            "Permeability",
            "Seismic BlueWhiteRed",
            "Time/Depth",
            "Stratigraphy",
            "Facies",
            "Gas-Oil-Water",
            "Gas-Water",
            "Oil-Water",
            "Accent",
        ]

        for idx, data in enumerate(selections):
            surfaceid = get_surface_id_from_data(data)

            use_stored_color_settings = (
                surfaceid in stored_color_settings
                and not data["reset_colors"]
                and not data["color_update"]
            )
            if not (links["colormap"] and idx > 0):

                colormap_value = (
                    stored_color_settings[surfaceid]["colormap"]
                    if use_stored_color_settings
                    else (
                        data["colormap"]["value"]
                        if "colormap" in data
                        else colormaps[0]
                    )
                )

            if not (links["color_range"] and idx > 0):
                selected_surface = get_surface_context_from_data(data)
                surface = ensemble_surface_providers[
                    selected_surface.ensemble
                ].get_surface(selected_surface)
                value_range = get_surface_range(surface)

                color_range = (
                    stored_color_settings[surfaceid]["color_range"]
                    if use_stored_color_settings
                    else (
                        value_range
                        if data["reset_colors"]
                        or (
                            not data["color_update"]
                            and not data.get("colormap_keep_range", {}).get("value")
                        )
                        else data["color_range"]["value"]
                    )
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
        if data["mode"]["value"] == SurfaceMode.STDDEV:
            surfaceid += data["mode"]["value"]
        return surfaceid


def view_layout(views, columns):
    """Convert a list of figures into a matrix for display"""
    columns = (
        columns
        if columns is not None
        else min([x for x in range(5) if (x * x) >= views])
    )
    rows = math.ceil(views / columns)
    return [rows, columns]
