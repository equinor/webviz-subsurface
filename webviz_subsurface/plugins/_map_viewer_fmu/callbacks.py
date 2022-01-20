from typing import Callable, Dict, List, Optional, Tuple, Any
from copy import deepcopy
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
        Output({"id": get_uuid(LayoutElements.VIEW_DATA), "tab": MATCH}, "data"),
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
        State({"id": get_uuid(LayoutElements.VIEW_DATA), "tab": MATCH}, "data"),
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
                id_values["selector"]: values
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
        Output({"id": get_uuid(LayoutElements.SELECTED_DATA), "tab": MATCH}, "data"),
        Output(selector_wrapper(MATCH), "children"),
        Output(
            {"id": get_uuid(LayoutElements.STORED_COLOR_SETTINGS), "tab": MATCH},
            "data",
        ),
        Input({"id": get_uuid(LayoutElements.VIEW_DATA), "tab": MATCH}, "data"),
        Input({"id": get_uuid(LayoutElements.MULTI), "tab": MATCH}, "value"),
        State(selector_wrapper(MATCH), "id"),
        State(
            {"id": get_uuid(LayoutElements.STORED_COLOR_SETTINGS), "tab": MATCH},
            "data",
        ),
        State(get_uuid("tabs"), "value"),
    )
    def _update_components_and_selected_data(
        view_selections, multi, wrapper_ids, stored_color_settings, tab
    ):
        ctx = callback_context.triggered[0]["prop_id"]
        if view_selections is None:
            raise PreventUpdate
        values, links = view_selections

        if "mode" in DefaultSettings.SELECTOR_DEFAULTS.get(tab, {}):
            for idx, data in enumerate(values):
                data["mode"] = DefaultSettings.SELECTOR_DEFAULTS[tab]["mode"][idx]

        multi_in_ctx = get_uuid(LayoutElements.MULTI) in ctx

        test, stored_color_settings = _update_data(
            values, links, multi, multi_in_ctx, stored_color_settings
        )
        #  stored_color_settings = _update_color_data(
        #      values, test, stored_color_settings, links
        #  )

        mapselections = test
        if multi is not None:
            mapselections = update_selections_with_multi(test, multi)

            ranges = []
            for data in mapselections:
                selected_surface = get_surface_context_from_data(data)
                surface = ensemble_surface_providers[
                    selected_surface.ensemble
                ].get_surface(selected_surface)
                ranges.append(get_surface_range(surface))

            if ranges:
                min_max_for_all = [
                    min(r[0] for r in ranges),
                    max(r[1] for r in ranges),
                ]
                test[0]["color_range"]["range"] = min_max_for_all
                test[0]["color_range"]["value"] = min_max_for_all

        return (
            mapselections,
            [
                SideBySideSelectorFlex(
                    tab,
                    get_uuid,
                    selector=id_val["selector"],
                    view_data=[data[id_val["selector"]] for data in test],
                    link=links[id_val.get("selector", False)],
                    dropdown=id_val["selector"] in ["ensemble", "mode", "colormap"],
                )
                for id_val in wrapper_ids
            ],
            stored_color_settings,
        )

    @callback(
        Output({"id": get_uuid(LayoutElements.DECKGLMAP), "tab": MATCH}, "layers"),
        Output({"id": get_uuid(LayoutElements.DECKGLMAP), "tab": MATCH}, "bounds"),
        Output({"id": get_uuid(LayoutElements.DECKGLMAP), "tab": MATCH}, "views"),
        Input({"id": get_uuid(LayoutElements.SELECTED_DATA), "tab": MATCH}, "data"),
        Input({"id": get_uuid(LayoutElements.VIEW_COLUMNS), "tab": MATCH}, "value"),
    )
    def _update_map(selections: dict, view_columns):
        if selections is None:
            raise PreventUpdate

        number_of_views = len(selections)
        if number_of_views == 0:
            number_of_views = 1

        layers = update_map_layers(number_of_views, well_set_model)
        layers = [json.loads(x.to_json()) for x in layers]
        layer_model = DeckGLMapLayersModel(layers)

        valid_data = []
        for idx, data in enumerate(selections):
            selected_surface = get_surface_context_from_data(data)

            ensemble = selected_surface.ensemble
            surface = ensemble_surface_providers[ensemble].get_surface(selected_surface)

            # HACK AT THE MOMENT
            if get_surface_range(surface) == [0.0, 0.0]:
                continue
            valid_data.append(idx)

            surface_range = get_surface_range(surface)

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
            property_bounds if valid_data else no_update,
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
                    if view in valid_data
                ],
            },
        )

    def _update_data(values, links, multi, multi_in_ctx, stored_color_settings) -> None:
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
        view_data = []
        for idx, data in enumerate(values):
            if not (links["ensemble"] and idx > 0):
                ensembles = list(ensemble_surface_providers.keys())
                ensemble = data.get("ensemble", [])
                if isinstance(ensemble, str):
                    ensemble = [ensemble]
                ensemble = [x for x in ensemble if x in ensembles]
                if not ensemble or multi_in_ctx:
                    ensemble = ensembles if multi == "ensemble" else ensembles[:1]

            if not (links["attribute"] and idx > 0):
                attributes = ensemble_surface_providers.get(ensemble[0]).attributes
                attribute = [x for x in data.get("attribute", []) if x in attributes]
                attribute = attribute if attribute else attributes[:1]

            if not (links["name"] and idx > 0):
                names = ensemble_surface_providers.get(ensemble[0]).names_in_attribute(
                    attribute[0]
                )
                name = [x for x in data.get("name", []) if x in names]
                if not name or multi_in_ctx:
                    name = names if multi == "name" else names[:1]

            if not (links["date"] and idx > 0):
                dates = ensemble_surface_providers.get(ensemble[0]).dates_in_attribute(
                    attribute[0]
                )
                dates = dates if dates is not None else []
                dates = [x for x in dates if not "_" in x] + [
                    x for x in dates if "_" in x
                ]

                date = [x for x in data.get("date", []) if x in dates]
                if not date or multi_in_ctx:
                    date = dates if multi == "date" else dates[:1]

            if not (links["mode"] and idx > 0):
                modes = [mode for mode in SurfaceMode]
                mode = data.get("mode", SurfaceMode.REALIZATION)

            if not (links["realizations"] and idx > 0):
                reals = ensemble_surface_providers[ensemble[0]].realizations

                if mode == SurfaceMode.REALIZATION:
                    real = [data.get("realizations", reals)[0]]
                else:
                    real = (
                        data["realizations"]
                        if "realizations" in data and len(data["realizations"]) > 1
                        else reals
                    )

            surfaceid = get_surface_id(attribute, name, date, mode)

            use_stored_color_settings = (
                surfaceid in stored_color_settings
                and not data["reset_colors"]
                and not data["color_update"]
            )
            if not (links["colormap"] and idx > 0):
                colormap_value = (
                    stored_color_settings[surfaceid]["colormap"]
                    if use_stored_color_settings
                    else (data.get("colormap", colormaps[0]))
                )

            if not (links["color_range"] and idx > 0):
                selected_surface = SurfaceContext(
                    attribute=attribute[0],
                    name=name[0],
                    date=date[0] if date else None,
                    ensemble=ensemble[0],
                    realizations=real,
                    mode=mode,
                )
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
                            and not data.get("colormap_keep_range", False)
                        )
                        else data["color_range"]
                    )
                )

            stored_color_settings[surfaceid] = {
                "colormap": colormap_value,
                "color_range": color_range,
            }

            view_data.append(
                {
                    "ensemble": {
                        "value": ensemble,
                        "options": ensembles,
                        "multi": multi == "ensemble",
                    },
                    "attribute": {"value": attribute, "options": attributes},
                    "name": {"value": name, "options": names, "multi": multi == "name"},
                    "date": {"value": date, "options": dates, "multi": multi == "date"},
                    "mode": {"value": mode, "options": modes},
                    "realizations": {
                        "value": real,
                        "options": reals,
                        "multi": mode != SurfaceMode.REALIZATION,
                    },
                    "colormap": {"value": colormap_value, "options": colormaps},
                    "color_range": {
                        "value": color_range,
                        "step": calculate_slider_step(
                            min_value=value_range[0],
                            max_value=value_range[1],
                            steps=100,
                        )
                        if value_range[0] != value_range[1]
                        else 0,
                        "range": value_range,
                    },
                }
            )

        return view_data, stored_color_settings

    def get_surface_context_from_data(data):
        return SurfaceContext(
            attribute=data["attribute"]["value"][0],
            name=data["name"]["value"][0],
            date=data["date"]["value"][0] if data["date"]["value"] else None,
            ensemble=data["ensemble"]["value"][0],
            realizations=data["realizations"]["value"],
            mode=data["mode"]["value"],
        )

    def get_surface_id(attribute, name, date, mode):
        surfaceid = attribute[0] + name[0]
        if date:
            surfaceid += date[0]
        if mode == SurfaceMode.STDDEV:
            surfaceid += mode
        return surfaceid

    def update_selections_with_multi(selections, multi):
        multi_values = selections[0][multi]["value"]
        new_selections = []
        for val in multi_values:
            updated_values = deepcopy(selections[0])
            updated_values[multi]["value"] = [val]
            new_selections.append(updated_values)
        return new_selections


def view_layout(views, columns):
    """Convert a list of figures into a matrix for display"""
    columns = (
        columns
        if columns is not None
        else min([x for x in range(5) if (x * x) >= views])
    )
    rows = math.ceil(views / columns)
    return [rows, columns]
