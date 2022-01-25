import statistics
from typing import Callable, Dict, List, Optional, Tuple, Any, Union
from copy import deepcopy
import json
import math

import numpy as np
from dash import Input, Output, State, callback, callback_context, no_update, ALL, MATCH
from dash.exceptions import PreventUpdate
from flask import url_for

from webviz_config.utils._dash_component_utils import calculate_slider_step

from webviz_subsurface._components.deckgl_map.deckgl_map_layers_model import (
    DeckGLMapLayersModel,
)
from webviz_subsurface._models.well_set_model import WellSetModel
from webviz_subsurface._providers.ensemble_surface_provider.surface_server import (
    SurfaceServer,
    QualifiedAddress,
    QualifiedDiffAddress,
)
from webviz_subsurface._providers.ensemble_surface_provider.ensemble_surface_provider import (
    SimulatedSurfaceAddress,
    StatisticalSurfaceAddress,
    ObservedSurfaceAddress,
)
from webviz_subsurface._providers import EnsembleSurfaceProvider
from .providers.ensemble_surface_provider import SurfaceMode
from .types import WellsContext
from .utils.formatting import format_date  # , update_nested_dict
from .layout import (
    LayoutElements,
    SideBySideSelectorFlex,
    update_map_layers,
    DefaultSettings,
    Tabs,
)


def plugin_callbacks(
    get_uuid: Callable,
    ensemble_surface_providers: Dict[str, EnsembleSurfaceProvider],
    surface_server: SurfaceServer,
    well_set_model: Optional[WellSetModel],
) -> None:
    def selections(tab, colorselector=False) -> Dict[str, str]:
        uuid = get_uuid(
            LayoutElements.SELECTIONS
            if not colorselector
            else LayoutElements.COLORSELECTIONS
        )
        return {"view": ALL, "id": uuid, "tab": tab, "selector": ALL}

    def selector_wrapper(tab, colorselector=False) -> Dict[str, str]:
        uuid = get_uuid(
            LayoutElements.WRAPPER if not colorselector else LayoutElements.COLORWRAPPER
        )
        return {"id": uuid, "tab": tab, "selector": ALL}

    def links(tab, colorselector=False) -> Dict[str, str]:
        uuid = get_uuid(
            LayoutElements.LINK if not colorselector else LayoutElements.COLORLINK
        )
        return {"id": uuid, "tab": tab, "selector": ALL}

    @callback(
        Output(get_uuid(LayoutElements.STORED_COLOR_SETTINGS), "data"),
        Input({"id": get_uuid(LayoutElements.SELECTED_DATA), "tab": ALL}, "data"),
        State(get_uuid("tabs"), "value"),
        State(get_uuid(LayoutElements.STORED_COLOR_SETTINGS), "data"),
        State({"id": get_uuid(LayoutElements.SELECTED_DATA), "tab": ALL}, "id"),
    )
    def _update_color_store(values, tab, stored_color_settings, data_id) -> dict:
        if values is None:
            raise PreventUpdate
        index = [x["tab"] for x in data_id].index(tab)

        stored_color_settings = (
            stored_color_settings if stored_color_settings is not None else {}
        )
        for data in values[index]:
            surfaceid = (
                get_surface_id_for_diff_surf(values[index])
                if data.get("surf_type") == "diff"
                else get_surface_id_from_data(data)
            )
            stored_color_settings[surfaceid] = {
                "colormap": data["colormap"],
                "color_range": data["color_range"],
            }

        return stored_color_settings

    @callback(
        Output({"id": get_uuid(LayoutElements.VIEW_DATA), "tab": MATCH}, "data"),
        Input(selections(MATCH), "value"),
        Input({"id": get_uuid(LayoutElements.WELLS), "tab": MATCH}, "value"),
        Input({"id": get_uuid(LayoutElements.VIEWS), "tab": MATCH}, "value"),
        Input(get_uuid("tabs"), "value"),
        State(selections(MATCH), "id"),
        State(links(MATCH), "id"),
    )
    def collect_selector_values(
        selector_values: list,
        selected_wells,
        number_of_views,
        tab,
        selector_ids,
        link_ids,
    ):

        datatab = link_ids[0]["tab"]
        if datatab != tab or number_of_views is None:
            raise PreventUpdate

        selections = []
        for idx in range(number_of_views):
            view_selections = {
                id_values["selector"]: values
                for values, id_values in zip(selector_values, selector_ids)
                if id_values["view"] == idx
            }
            view_selections["wells"] = selected_wells
            selections.append(view_selections)

        return selections

    @callback(
        Output({"id": get_uuid(LayoutElements.SELECTORVALUES), "tab": MATCH}, "data"),
        Output(selector_wrapper(MATCH), "children"),
        Input({"id": get_uuid(LayoutElements.VIEW_DATA), "tab": MATCH}, "data"),
        Input({"id": get_uuid(LayoutElements.MULTI), "tab": MATCH}, "value"),
        Input(links(MATCH), "value"),
        State(selector_wrapper(MATCH), "id"),
        State(get_uuid("tabs"), "value"),
    )
    def _update_components_and_selected_data(
        values,
        multi,
        selectorlinks,
        wrapper_ids,
        tab,
    ):
        ctx = callback_context.triggered[0]["prop_id"]

        if values is None:
            raise PreventUpdate

        links = [l[0] for l in selectorlinks if l]

        if "mode" in DefaultSettings.SELECTOR_DEFAULTS.get(tab, {}):
            for idx, data in enumerate(values):
                data["mode"] = DefaultSettings.SELECTOR_DEFAULTS[tab]["mode"][idx]

        multi_in_ctx = get_uuid(LayoutElements.MULTI) in ctx
        test = _update_data(values, links, multi, multi_in_ctx)

        for idx, data in enumerate(test):
            for key, val in data.items():
                values[idx][key] = val["value"]

        if multi is not None:
            values = update_selections_with_multi(values, multi)
        values = remove_data_if_not_valid(values, tab)

        return (
            values,
            [
                SideBySideSelectorFlex(
                    tab,
                    get_uuid,
                    selector=id_val["selector"],
                    view_data=[data[id_val["selector"]] for data in test],
                    link=id_val["selector"] in links,
                    dropdown=id_val["selector"] in ["ensemble", "mode", "colormap"],
                )
                for id_val in wrapper_ids
            ],
        )

    @callback(
        Output({"id": get_uuid(LayoutElements.SELECTED_DATA), "tab": MATCH}, "data"),
        Output(selector_wrapper(MATCH, colorselector=True), "children"),
        Input({"id": get_uuid(LayoutElements.SELECTORVALUES), "tab": MATCH}, "data"),
        Input(selections(MATCH, colorselector=True), "value"),
        Input(
            {"view": ALL, "id": get_uuid(LayoutElements.RANGE_RESET), "tab": MATCH},
            "n_clicks",
        ),
        Input(links(MATCH, colorselector=True), "value"),
        State({"id": get_uuid(LayoutElements.MULTI), "tab": MATCH}, "value"),
        State(selector_wrapper(MATCH, colorselector=True), "id"),
        State(get_uuid(LayoutElements.STORED_COLOR_SETTINGS), "data"),
        State(get_uuid("tabs"), "value"),
        State(selections(MATCH, colorselector=True), "id"),
    )
    def _update_color_components_and_value(
        values,
        colorvalues,
        _n_click,
        colorlinks,
        multi,
        color_wrapper_ids,
        stored_color_settings,
        tab,
        colorval_ids,
    ):
        ctx = callback_context.triggered[0]["prop_id"]

        if values is None:
            raise PreventUpdate

        reset_color_index = (
            json.loads(ctx.split(".")[0])["view"]
            if get_uuid(LayoutElements.RANGE_RESET) in ctx
            else None
        )
        color_update_index = (
            json.loads(ctx.split(".")[0]).get("view")
            if LayoutElements.COLORSELECTIONS in ctx
            else None
        )

        links = [l[0] for l in colorlinks if l]

        for idx, data in enumerate(values):
            data.update(
                {
                    id_values["selector"]: values
                    for values, id_values in zip(colorvalues, colorval_ids)
                    if id_values["view"] == idx
                }
            )

        if multi is not None and multi != "attribute":
            links.append("color_range")
            ranges = [data["surface_range"] for data in values]
            if ranges:
                min_max_for_all = [min(r[0] for r in ranges), max(r[1] for r in ranges)]

        color_test = _update_colors(
            values,
            links,
            stored_color_settings,
            reset_color_index,
            color_update=color_update_index,
        )

        for idx, data in enumerate(color_test):
            if multi is not None and multi != "attribute":
                data["color_range"]["range"] = min_max_for_all
                if reset_color_index is not None:
                    data["color_range"]["value"] = min_max_for_all
            for key, val in data.items():
                values[idx][key] = val["value"]

        return (
            values,
            [
                SideBySideSelectorFlex(
                    tab,
                    get_uuid,
                    selector=id_val["selector"],
                    view_data=[data[id_val["selector"]] for data in color_test],
                    link=id_val["selector"] in links,
                    dropdown=id_val["selector"] in ["colormap"],
                )
                for id_val in color_wrapper_ids
            ],
        )

    @callback(
        Output({"id": get_uuid(LayoutElements.DECKGLMAP), "tab": MATCH}, "layers"),
        Output({"id": get_uuid(LayoutElements.DECKGLMAP), "tab": MATCH}, "bounds"),
        Output({"id": get_uuid(LayoutElements.DECKGLMAP), "tab": MATCH}, "views"),
        Input({"id": get_uuid(LayoutElements.SELECTED_DATA), "tab": MATCH}, "data"),
        Input({"id": get_uuid(LayoutElements.VIEW_COLUMNS), "tab": MATCH}, "value"),
        State(get_uuid("tabs"), "value"),
    )
    def _update_map(values: dict, view_columns, tab_name):

        if values is None:
            raise PreventUpdate

        number_of_views = len(values) if values else 1

        layers = update_map_layers(number_of_views, well_set_model)
        layers = [json.loads(x.to_json()) for x in layers]
        layer_model = DeckGLMapLayersModel(layers)

        for idx, data in enumerate(values):
            if data.get("surf_type") != "diff":
                surface_address = get_surface_context_from_data(data)

                provider = ensemble_surface_providers[data["ensemble"][0]]
                provider_id: str = provider.provider_id()

                qualified_address: Union[QualifiedAddress, QualifiedDiffAddress]
                qualified_address = QualifiedAddress(provider_id, surface_address)

                surf_meta = surface_server.get_surface_metadata(qualified_address)

                if not surf_meta:
                    # This means we need to compute the surface
                    surface = provider.get_surface(address=surface_address)
                    if not surface:
                        raise ValueError(
                            f"Could not get surface for address: {surface_address}"
                        )

                    surface_server.publish_surface(qualified_address, surface)
                    surf_meta = surface_server.get_surface_metadata(qualified_address)
            else:
                # Calculate and add layers for difference map.
                # Mostly duplicate code to the above. Should be improved.
                surface_address = get_surface_context_from_data(values[0])
                subsurface_address = get_surface_context_from_data(values[1])
                provider = ensemble_surface_providers[values[0]["ensemble"][0]]
                subprovider = ensemble_surface_providers[values[1]["ensemble"][0]]
                provider_id: str = provider.provider_id()
                subprovider_id = subprovider.provider_id()
                qualified_address: Union[QualifiedAddress, QualifiedDiffAddress]

                qualified_address = QualifiedDiffAddress(
                    provider_id, surface_address, subprovider_id, subsurface_address
                )

                surf_meta = surface_server.get_surface_metadata(qualified_address)
                if not surf_meta:
                    surface_a = provider.get_surface(address=surface_address)
                    surface_b = subprovider.get_surface(address=subsurface_address)
                    surface = surface_a - surface_b

                    surface_server.publish_surface(qualified_address, surface)
                    surf_meta = surface_server.get_surface_metadata(qualified_address)

            viewport_bounds = [
                surf_meta.x_min,
                surf_meta.y_min,
                surf_meta.x_max,
                surf_meta.y_max,
            ]

            layer_data = {
                "image": surface_server.encode_partial_url(qualified_address),
                "bounds": surf_meta.deckgl_bounds,
                "rotDeg": surf_meta.deckgl_rot_deg,
                "valueRange": [surf_meta.val_min, surf_meta.val_max],
            }

            layer_model.update_layer_by_id(
                layer_id=f"{LayoutElements.COLORMAP_LAYER}-{idx}",
                layer_data=layer_data,
            )
            layer_model.update_layer_by_id(
                layer_id=f"{LayoutElements.HILLSHADING_LAYER}-{idx}",
                layer_data=layer_data,
            )
            layer_model.update_layer_by_id(
                layer_id=f"{LayoutElements.COLORMAP_LAYER}-{idx}",
                layer_data={
                    "colorMapName": data["colormap"],
                    "colorMapRange": data["color_range"],
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
            viewport_bounds if values else no_update,
            {
                "layout": view_layout(number_of_views, view_columns),
                "viewports": [
                    {
                        "id": f"{view}_view",
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

    def _update_data(values, links, multi, multi_in_ctx) -> None:
        view_data = []
        for idx, data in enumerate(values):

            if not ("ensemble" in links and idx > 0):
                ensembles = list(ensemble_surface_providers.keys())
                ensemble = data.get("ensemble", [])
                ensemble = [ensemble] if isinstance(ensemble, str) else ensemble
                if not ensemble or multi_in_ctx:
                    ensemble = ensembles if multi == "ensemble" else ensembles[:1]

            if not ("attribute" in links and idx > 0):
                attributes = []
                for ens in ensemble:
                    provider = ensemble_surface_providers[ens]
                    attributes.extend(
                        [x for x in provider.attributes() if x not in attributes]
                    )
                    # only show attributes with date when multi is set to date
                    if multi == "date":
                        attributes = [
                            x for x in attributes if attribute_has_date(x, provider)
                        ]

                attribute = [x for x in data.get("attribute", []) if x in attributes]
                if not attribute or multi_in_ctx:
                    attribute = attributes if multi == "attribute" else attributes[:1]

            if not ("name" in links and idx > 0):
                names = []
                for ens in ensemble:
                    provider = ensemble_surface_providers[ens]
                    for attr in attribute:
                        attr_names = provider.surface_names_for_attribute(attr)
                        names.extend([x for x in attr_names if x not in names])

                name = [x for x in data.get("name", []) if x in names]
                if not name or multi_in_ctx:
                    name = names if multi == "name" else names[:1]

            if not ("date" in links and idx > 0):
                dates = []
                for ens in ensemble:
                    provider = ensemble_surface_providers[ens]
                    for attr in attribute:
                        attr_dates = provider.surface_dates_for_attribute(attr)
                        # EMPTY STRING returned ... not None anymore?
                        if bool(attr_dates[0]):
                            dates.extend([x for x in attr_dates if x not in dates])

                interval_dates = [x for x in dates if "_" in x]
                dates = [x for x in dates if x not in interval_dates] + interval_dates

                date = [x for x in data.get("date", []) if x in dates]
                if not date or multi_in_ctx:
                    date = dates if multi == "date" else dates[:1]

            if not ("mode" in links and idx > 0):
                modes = [mode for mode in SurfaceMode]
                mode = data.get("mode", SurfaceMode.REALIZATION)

            if not ("realizations" in links and idx > 0):
                reals = []
                for ens in ensembles:
                    provider = ensemble_surface_providers[ens]
                    reals.extend([x for x in provider.realizations() if x not in reals])

                if mode == SurfaceMode.REALIZATION and multi != "realizations":
                    real = [data.get("realizations", reals)[0]]
                else:
                    real = (
                        data["realizations"]
                        if "realizations" in data and len(data["realizations"]) > 1
                        else reals
                    )
                # FIX THIS
                if multi_in_ctx:
                    # real = [x for x in data.get("realizations", [])]
                    real = reals if multi == "realizations" else reals[:1]

            view_data.append(
                {
                    "ensemble": {
                        "value": ensemble,
                        "options": ensembles,
                        "multi": multi == "ensemble",
                    },
                    "attribute": {
                        "value": attribute,
                        "options": attributes,
                        "multi": multi == "attribute",
                    },
                    "name": {"value": name, "options": names, "multi": multi == "name"},
                    "date": {"value": date, "options": dates, "multi": multi == "date"},
                    "mode": {"value": mode, "options": modes},
                    "realizations": {
                        "value": real,
                        "options": reals,
                        "multi": mode != SurfaceMode.REALIZATION
                        or multi == "realizations",
                    },
                }
            )

        return view_data

    def _update_colors(
        values,
        links,
        stored_color_settings,
        reset_color_index=None,
        color_update=False,
    ) -> None:
        stored_color_settings = (
            stored_color_settings if stored_color_settings is not None else {}
        )

        colormaps = DefaultSettings.COLORMAP_OPTIONS

        surfids = []
        color_data = []
        for idx, data in enumerate(values):
            surfaceid = (
                get_surface_id_for_diff_surf(values)
                if data.get("surf_type") == "diff"
                else get_surface_id_from_data(data)
            )
            if surfaceid in surfids:
                index_of_first = surfids.index(surfaceid)
                surfids.append(surfaceid)
                color_data.append(color_data[index_of_first].copy())
                continue

            surfids.append(surfaceid)

            use_stored_color = (
                surfaceid in stored_color_settings and not color_update == idx
            )
            if not ("colormap" in links and idx > 0):
                colormap = (
                    stored_color_settings[surfaceid]["colormap"]
                    if use_stored_color
                    else data.get("colormap", colormaps[0])
                )

            if not ("color_range" in links and idx > 0):
                value_range = data["surface_range"]

                if data.get("colormap_keep_range", False):
                    color_range = data["color_range"]
                elif reset_color_index == idx or surfaceid not in stored_color_settings:
                    color_range = value_range
                else:
                    color_range = (
                        stored_color_settings[surfaceid]["color_range"]
                        if use_stored_color
                        else data.get("color_range", value_range)
                    )

            color_data.append(
                {
                    "colormap": {"value": colormap, "options": colormaps},
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

        return color_data

    def get_surface_context_from_data(data):
        has_date = bool(
            ensemble_surface_providers.get(
                data["ensemble"][0]
            ).surface_dates_for_attribute(data["attribute"][0])[0]
        )

        if data["mode"] == SurfaceMode.REALIZATION:
            return SimulatedSurfaceAddress(
                attribute=data["attribute"][0],
                name=data["name"][0],
                datestr=data["date"][0] if has_date else None,
                realization=data["realizations"][0],
            )
        if data["mode"] == SurfaceMode.OBSERVED:
            return ObservedSurfaceAddress(
                attribute=data["attribute"][0],
                name=data["name"][0],
                datestr=data["date"][0] if has_date else None,
            )
        return StatisticalSurfaceAddress(
            attribute=data["attribute"][0],
            name=data["name"][0],
            datestr=data["date"][0] if has_date else None,
            realizations=data["realizations"],
            statistic=data["mode"],
        )

    def get_surface_id_from_data(data):
        surfaceid = data["attribute"][0] + data["name"][0]
        if data["date"]:
            surfaceid += data["date"][0]
        if data["mode"] == SurfaceMode.STDDEV:
            surfaceid += data["mode"]
        return surfaceid

    def get_surface_id_for_diff_surf(values):
        surfaceid = ""
        for data in values[:2]:
            surfaceid += data["attribute"][0] + data["name"][0]
            if data["date"]:
                surfaceid += data["date"][0]
            if data["mode"] == SurfaceMode.STDDEV:
                surfaceid += data["mode"]
        return surfaceid

    def update_selections_with_multi(values, multi):
        multi_values = values[0][multi]
        new_values = []
        for val in multi_values:
            updated_values = deepcopy(values[0])
            updated_values[multi] = [val]
            new_values.append(updated_values)
        return new_values

    def attribute_has_date(attribute, provider):
        return bool(provider.surface_dates_for_attribute(attribute)[0])

    def remove_data_if_not_valid(values, tab):
        updated_values = []
        surfaces = []
        for data in values:
            selected_surface = get_surface_context_from_data(data)
            try:
                surface = ensemble_surface_providers[data["ensemble"][0]].get_surface(
                    selected_surface
                )
            except ValueError:
                continue

            if surface is not None and not surface.values.mask.all():
                data["surface_range"] = [
                    np.nanmin(surface.values),
                    np.nanmax(surface.values),
                ]
                surfaces.append(surface)
                updated_values.append(data)

        if tab == Tabs.DIFF and len(surfaces) == 2:
            diff_surf = surfaces[0] - surfaces[1]
            updated_values.append(
                {
                    "surface_range": [
                        np.nanmin(diff_surf.values),
                        np.nanmax(diff_surf.values),
                    ],
                    "surf_type": "diff",
                }
            )

        return updated_values


def view_layout(views, columns):
    """Convert a list of figures into a matrix for display"""
    columns = (
        columns
        if columns is not None
        else min([x for x in range(20) if (x * x) >= views])
    )
    rows = math.ceil(views / columns)
    return [rows, columns]
