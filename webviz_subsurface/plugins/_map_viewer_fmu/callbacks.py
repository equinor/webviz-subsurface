# pylint: disable=too-many-lines
import base64
import io
import json
import math
import zipfile
from copy import deepcopy
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import webviz_subsurface_components as wsc
from dash import ALL, MATCH, Input, Output, State, callback, callback_context, no_update
from dash.exceptions import PreventUpdate
from webviz_config import EncodedFile
from webviz_config.utils._dash_component_utils import calculate_slider_step

from webviz_subsurface._providers import (
    EnsembleFaultPolygonsProvider,
    EnsembleSurfaceProvider,
    FaultPolygonsServer,
    ObservedSurfaceAddress,
    QualifiedDiffSurfaceAddress,
    QualifiedSurfaceAddress,
    SimulatedFaultPolygonsAddress,
    SimulatedSurfaceAddress,
    StatisticalSurfaceAddress,
    SurfaceAddress,
    SurfaceArrayServer,
    SurfaceImageServer,
)

from ._layer_model import DeckGLMapLayersModel
from ._tmp_well_pick_provider import WellPickProvider
from ._types import LayerTypes, SurfaceMode
from ._utils import round_to_significant
from .layout import (
    DefaultSettings,
    LayoutElements,
    LayoutLabels,
    SideBySideColorSelectorFlex,
    SideBySideSelectorFlex,
    Tabs,
    update_map_layers,
)


# pylint: disable=too-many-locals,too-many-statements, too-many-arguments
def plugin_callbacks(
    get_uuid: Callable,
    ensemble_surface_providers: Dict[str, EnsembleSurfaceProvider],
    surface_server: Union[SurfaceArrayServer, SurfaceImageServer],
    ensemble_fault_polygons_providers: Dict[str, EnsembleFaultPolygonsProvider],
    fault_polygons_server: FaultPolygonsServer,
    map_surface_names_to_fault_polygons: Dict[str, str],
    well_picks_provider: Optional[WellPickProvider],
    fault_polygon_attribute: Optional[str],
    color_tables: List[Dict],
    plugin_data_output: Output,
    plugin_data_requested: Input,
) -> None:
    def selections(tab: str, colorselector: bool = False) -> Dict[str, str]:
        uuid = get_uuid(
            LayoutElements.SELECTIONS
            if not colorselector
            else LayoutElements.COLORSELECTIONS
        )
        return {"view": ALL, "id": uuid, "tab": tab, "selector": ALL}

    def selector_wrapper(tab: str, colorselector: bool = False) -> Dict[str, str]:
        uuid = get_uuid(
            LayoutElements.WRAPPER if not colorselector else LayoutElements.COLORWRAPPER
        )
        return {"id": uuid, "tab": tab, "selector": ALL}

    def links(tab: str, colorselector: bool = False) -> Dict[str, str]:
        uuid = get_uuid(
            LayoutElements.LINK if not colorselector else LayoutElements.COLORLINK
        )
        return {"id": uuid, "tab": tab, "selector": ALL}

    @callback(
        Output(get_uuid(LayoutElements.OPTIONS_DIALOG), "open"),
        Input({"id": get_uuid("Button"), "tab": ALL}, "n_clicks"),
        State(get_uuid(LayoutElements.OPTIONS_DIALOG), "open"),
    )
    def open_close_options_dialog(_n_click: list, is_open: bool) -> bool:
        if any(click is not None for click in _n_click):
            return not is_open
        raise PreventUpdate

    # 2nd callback
    @callback(
        Output({"id": get_uuid(LayoutElements.LINKED_VIEW_DATA), "tab": MATCH}, "data"),
        Output(selector_wrapper(MATCH), "children"),
        Input(selections(MATCH), "value"),
        Input({"id": get_uuid(LayoutElements.VIEWS), "tab": MATCH}, "value"),
        Input({"id": get_uuid(LayoutElements.MULTI), "tab": MATCH}, "value"),
        Input(links(MATCH), "value"),
        Input(get_uuid(LayoutElements.REALIZATIONS_FILTER), "value"),
        Input(get_uuid("tabs"), "value"),
        State(selections(MATCH), "id"),
        State(selector_wrapper(MATCH), "id"),
    )
    def _update_components_and_selected_data(
        mapselector_values: List[Dict[str, Any]],
        number_of_views: int,
        multi_selector: str,
        selectorlinks: List[List[str]],
        filtered_reals: List[int],
        tab_name: str,
        selector_ids: List[dict],
        wrapper_ids: List[dict],
    ) -> Tuple[List[dict], list]:
        """Reads stored raw selections, stores valid selections as a dcc.Store
        and updates visible and valid selections in layout"""

        # Prevent update if the pattern matched components does not match the current tab
        datatab = wrapper_ids[0]["tab"]
        if datatab != tab_name or number_of_views is None:
            raise PreventUpdate

        ctx = callback_context.triggered[0]["prop_id"]

        selector_values = []
        for idx in range(number_of_views):
            view_selections = combine_selector_values_and_name(
                mapselector_values, selector_ids, view=idx
            )
            view_selections["multi"] = multi_selector
            if tab_name == Tabs.STATS:
                view_selections["mode"] = DefaultSettings.VIEW_LAYOUT_STATISTICS_TAB[
                    idx
                ]
            selector_values.append(view_selections)

        linked_selector_names = [l[0] for l in selectorlinks if l]

        component_properties = _update_selector_component_properties_from_provider(
            selector_values=selector_values,
            linked_selectors=linked_selector_names,
            multi=multi_selector,
            multi_in_ctx=get_uuid(LayoutElements.MULTI) in ctx,
            filtered_realizations=filtered_reals,
        )
        # retrive the updated selector values from the component properties
        selector_values = [
            {key: val["value"] for key, val in data.items()}
            for idx, data in enumerate(component_properties)
        ]

        if multi_selector is not None:
            selector_values = update_selections_with_multi(
                selector_values, multi_selector
            )
        selector_values = remove_data_if_not_valid(selector_values)
        if tab_name == Tabs.DIFF and len(selector_values) == 2:
            selector_values = add_diff_surface_to_values(selector_values)

        return (
            selector_values,
            [
                SideBySideSelectorFlex(
                    tab_name,
                    get_uuid,
                    selector=id_val["selector"],
                    view_data=[
                        data[id_val["selector"]] for data in component_properties
                    ],
                    link=id_val["selector"] in linked_selector_names,
                    dropdown=id_val["selector"] in ["ensemble", "mode"],
                )
                for id_val in wrapper_ids
            ],
        )

    @callback(
        Output(
            {
                "view": MATCH,
                "id": get_uuid("color-input-min"),
                "tab": MATCH,
            },
            "value",
        ),
        Output(
            {
                "view": MATCH,
                "id": get_uuid("color-input-max"),
                "tab": MATCH,
            },
            "value",
        ),
        Output(
            {
                "view": MATCH,
                "id": get_uuid(LayoutElements.COLORSELECTIONS),
                "selector": "color_range",
                "tab": MATCH,
            },
            "value",
        ),
        Input(
            {
                "view": MATCH,
                "id": get_uuid("color-input-min"),
                "tab": MATCH,
            },
            "value",
        ),
        Input(
            {
                "view": MATCH,
                "id": get_uuid("color-input-max"),
                "tab": MATCH,
            },
            "value",
        ),
        Input(
            {
                "view": MATCH,
                "id": get_uuid(LayoutElements.COLORSELECTIONS),
                "selector": "color_range",
                "tab": MATCH,
            },
            "value",
        ),
    )
    def color_inputs_to_color_range(
        min_value: float, max_value: float, color_range: List[float]
    ) -> Tuple[float, float, List[float]]:
        """Updates color_range with the values from the color inputs"""

        try:
            min_value = round_to_significant(float(min_value))
            max_value = round_to_significant(float(max_value))
            color_range = [round_to_significant(float(val)) for val in color_range]
        except ValueError:
            return no_update, no_update, no_update

        ctx = callback_context.triggered
        if "color-input-min" in ctx[0]["prop_id"]:
            return no_update, no_update, [min_value, color_range[1]]
        if "color-input-max" in ctx[0]["prop_id"]:
            return no_update, no_update, [color_range[0], max_value]
        if "color_range" in ctx[0]["prop_id"]:
            return color_range[0], color_range[1], color_range
        return no_update, no_update, no_update

    # 3rd callback
    @callback(
        Output(
            {"id": get_uuid(LayoutElements.VERIFIED_VIEW_DATA), "tab": MATCH}, "data"
        ),
        Output(selector_wrapper(MATCH, colorselector=True), "children"),
        Input({"id": get_uuid(LayoutElements.LINKED_VIEW_DATA), "tab": MATCH}, "data"),
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
        selector_values: List[dict],
        colorvalues: List[Dict[str, Any]],
        _n_click: int,
        colorlinks: List[List[str]],
        multi: str,
        color_wrapper_ids: List[dict],
        stored_color_settings: Dict,
        tab: str,
        colorval_ids: List[dict],
    ) -> Tuple[List[dict], list]:
        """Adds color settings to validated stored selections, updates color component in layout
        and writes validated selectors with colors to a dcc.Store"""
        ctx = callback_context.triggered[0]["prop_id"]

        if selector_values is None:
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

        # if a selector is set as multi in the "Maps per Selector" tab
        # color_range should be linked and the min and max surface ranges
        # from all the views should be used as range
        use_range_from_all = tab == Tabs.SPLIT and multi != "attribute"

        links = [l[0] for l in colorlinks if l]
        links = links if not use_range_from_all else links + ["color_range"]

        # update selector_values with current values from the color components
        for idx, data in enumerate(selector_values):
            data.update(
                combine_selector_values_and_name(colorvalues, colorval_ids, view=idx)
            )
        color_component_properties = _update_color_component_properties(
            values=selector_values,
            links=links if not use_range_from_all else links + ["color_range"],
            stored_color_settings=stored_color_settings,
            reset_color_index=reset_color_index,
            color_update_index=color_update_index,
        )

        if use_range_from_all:
            ranges = [data["surface_range"] for data in selector_values]
            min_max_for_all = [min(r[0] for r in ranges), max(r[1] for r in ranges)]
            for data in color_component_properties:
                data["color_range"]["range"] = min_max_for_all
                if reset_color_index is not None:
                    data["color_range"]["value"] = min_max_for_all

        for idx, data in enumerate(color_component_properties):
            for key, val in data.items():
                selector_values[idx][key] = val["value"]

        return (
            selector_values,
            [
                SideBySideColorSelectorFlex(
                    tab,
                    get_uuid,
                    selector=id_val["selector"],
                    view_data=[
                        data[id_val["selector"]] for data in color_component_properties
                    ],
                    link=id_val["selector"] in links,
                    color_tables=color_tables,
                )
                for id_val in color_wrapper_ids
            ],
        )

    # 4th callback
    @callback(
        Output(get_uuid(LayoutElements.STORED_COLOR_SETTINGS), "data"),
        Input({"id": get_uuid(LayoutElements.VERIFIED_VIEW_DATA), "tab": ALL}, "data"),
        State(get_uuid("tabs"), "value"),
        State(get_uuid(LayoutElements.STORED_COLOR_SETTINGS), "data"),
        State({"id": get_uuid(LayoutElements.VERIFIED_VIEW_DATA), "tab": ALL}, "id"),
    )
    def _update_color_store(
        selector_values: List[List[dict]],
        tab: str,
        stored_color_settings: Dict[str, dict],
        data_id: List[dict],
    ) -> Dict[str, dict]:
        """Update the color store with chosen color range and colormap for surfaces"""
        if selector_values is None:
            raise PreventUpdate
        index = [x["tab"] for x in data_id].index(tab)

        stored_color_settings = (
            stored_color_settings if stored_color_settings is not None else {}
        )
        for data in selector_values[index]:
            surfaceid = (
                get_surface_id_for_diff_surf(selector_values[index])
                if data.get("surf_type") == "diff"
                else get_surface_id_from_data(data)
            )
            stored_color_settings[surfaceid] = {
                "colormap": data["colormap"],
                "color_range": data["color_range"],
            }

        return stored_color_settings

    # 5th callback
    @callback(
        Output({"id": get_uuid(LayoutElements.DECKGLMAP), "tab": MATCH}, "layers"),
        Output({"id": get_uuid(LayoutElements.DECKGLMAP), "tab": MATCH}, "bounds"),
        Output({"id": get_uuid(LayoutElements.DECKGLMAP), "tab": MATCH}, "views"),
        Output({"id": get_uuid(LayoutElements.DECKGLMAP), "tab": MATCH}, "children"),
        Input(
            {"id": get_uuid(LayoutElements.VERIFIED_VIEW_DATA), "tab": MATCH}, "data"
        ),
        Input(get_uuid(LayoutElements.WELLS), "value"),
        Input(get_uuid(LayoutElements.VIEW_COLUMNS), "value"),
        Input(get_uuid(LayoutElements.OPTIONS), "value"),
        State(get_uuid("tabs"), "value"),
        State({"id": get_uuid(LayoutElements.MULTI), "tab": MATCH}, "value"),
        State({"id": get_uuid(LayoutElements.DECKGLMAP), "tab": MATCH}, "bounds"),
        State({"id": get_uuid(LayoutElements.DECKGLMAP), "tab": MATCH}, "views"),
    )
    # pylint: disable=too-many-branches
    def _update_map(
        surface_elements: List[dict],
        selected_wells: List[str],
        view_columns: Optional[int],
        options: List[str],
        tab_name: str,
        multi: str,
        current_bounds: Optional[List],
        current_views: Optional[dict],
    ) -> tuple:
        """Updates the map component with the stored, validated selections"""

        # Prevent update if the pattern matched components does not match the current tab
        state_list = callback_context.states_list
        if state_list[1]["id"]["tab"] != tab_name or surface_elements is None:
            raise PreventUpdate

        if tab_name == Tabs.DIFF:
            view_columns = 3 if view_columns is None else view_columns

        layers = update_map_layers(
            render_surfaces_as_images=isinstance(surface_server, SurfaceImageServer),
            views=len(surface_elements),
            include_well_layer=well_picks_provider is not None,
            visible_well_layer=LayoutLabels.SHOW_WELLS in options,
            visible_fault_polygons_layer=LayoutLabels.SHOW_FAULTPOLYGONS in options,
        )
        layer_model = DeckGLMapLayersModel(layers)

        for idx, data in enumerate(surface_elements):
            diff_surf = data.get("surf_type") == "diff"
            surf_meta, surface_url = (
                get_surface_metadata_and_image(data)
                if not diff_surf
                else get_surface_metadata_and_image_for_diff_surface(surface_elements)
            )
            viewport_bounds = [
                surf_meta.x_min,
                surf_meta.y_min,
                surf_meta.x_max,
                surf_meta.y_max,
            ]
            if (
                data["color_range"][0] != surf_meta.val_min
                or data["color_range"][1] != surf_meta.val_max
            ):
                color_range = data["color_range"]
            else:
                color_range = None
            if isinstance(surface_server, SurfaceArrayServer):
                layer_data = {
                    "meshUrl": surface_url,
                    "frame": {
                        "origin": [surf_meta.x_ori, surf_meta.y_ori],
                        "count": [surf_meta.x_count, surf_meta.y_count],
                        "increment": [surf_meta.x_inc, surf_meta.y_inc],
                        "rotDeg": surf_meta.rot_deg,
                    },
                    "colorMapName": data["colormap"],
                    "colorMapRange": color_range,
                }
                layer_idx = None
                for layer in layers:
                    if layer["id"] == f"{LayoutElements.MAP3D_LAYER}-{idx}":
                        layer_idx = layers.index(layer)
                        break
                if layer_idx is not None:
                    layers[layer_idx].update(layer_data)
                else:
                    layer_data["id"] = f"{LayoutElements.MAP3D_LAYER}-{idx}"
                    layer_data["@@type"] = LayerTypes.MAP3D
                    layer_data["material"] = False
                    layers.insert(0, layer_data)
            else:
                layer_data = {
                    "image": surface_url,
                    "bounds": surf_meta.deckgl_bounds,
                    "rotDeg": surf_meta.deckgl_rot_deg,
                    "valueRange": [surf_meta.val_min, surf_meta.val_max],
                    "colorMapName": data["colormap"],
                    "colorMapRange": color_range,
                }
                layer_model.update_layer_by_id(
                    layer_id=f"{LayoutElements.COLORMAP_LAYER}-{idx}",
                    layer_data=layer_data,
                )
            if (
                LayoutLabels.SHOW_FAULTPOLYGONS in options
                and fault_polygon_attribute is not None
            ):
                # if diff surface use polygons from first view
                data_for_faultpolygons = data if not diff_surf else surface_elements[0]
                fault_polygons_provider = ensemble_fault_polygons_providers[
                    data_for_faultpolygons["ensemble"][0]
                ]
                horizon_name = data_for_faultpolygons["name"][0]
                fault_polygons_address = SimulatedFaultPolygonsAddress(
                    attribute=fault_polygon_attribute,
                    name=map_surface_names_to_fault_polygons.get(
                        horizon_name, horizon_name
                    ),
                    realization=int(data_for_faultpolygons["realizations"][0]),
                )
                layer_model.update_layer_by_id(
                    layer_id=f"{LayoutElements.FAULTPOLYGONS_LAYER}-{idx}",
                    layer_data={
                        "data": fault_polygons_server.encode_partial_url(
                            provider_id=fault_polygons_provider.provider_id(),
                            fault_polygons_address=fault_polygons_address,
                        ),
                    },
                )
            if LayoutLabels.SHOW_WELLS in options and well_picks_provider is not None:
                horizon_name = (
                    data["name"][0] if not diff_surf else surface_elements[0]["name"][0]
                )
                layer_model.update_layer_by_id(
                    layer_id=f"{LayoutElements.WELLS_LAYER}-{idx}",
                    layer_data={
                        "data": well_picks_provider.get_geojson(
                            selected_wells, horizon_name
                        )
                    },
                )
        viewports = []
        view_annotations = []
        for idx, data in enumerate(surface_elements):
            view_annotations.append(
                wsc.ViewAnnotation(
                    id=f"{idx}_view",
                    children=[
                        wsc.WebVizColorLegend(
                            min=data["color_range"][0],
                            max=data["color_range"][1],
                            colorName=data["colormap"],
                            cssLegendStyles={"top": "0", "right": "0"},
                            openColorSelector=False,
                            legendScaleSize=0.1,
                            legendFontSize=30,
                            colorTables=color_tables,
                        ),
                        wsc.ViewFooter(
                            children=make_viewport_label(
                                surface_elements[idx], tab_name, multi
                            )
                        ),
                    ],
                )
            )
            viewports.append(
                {
                    "id": f"{idx}_view",
                    "show3D": False,
                    "isSync": True,
                    "layerIds": [
                        f"{LayoutElements.MAP3D_LAYER}-{idx}"
                        if isinstance(surface_server, SurfaceArrayServer)
                        else f"{LayoutElements.COLORMAP_LAYER}-{idx}",
                        f"{LayoutElements.FAULTPOLYGONS_LAYER}-{idx}",
                        f"{LayoutElements.WELLS_LAYER}-{idx}",
                    ],
                    "name": make_viewport_label(surface_elements[idx], tab_name, multi),
                }
            )
        updated_view_layout = view_layout(len(surface_elements), view_columns)
        if (
            current_views
            and updated_view_layout == current_views["layout"]
            and len(current_views["viewports"]) == len(viewports)
        ):
            updated_views = no_update

        else:
            updated_views = {
                "layout": updated_view_layout,
                "showLabel": True,
                "viewports": viewports,
            }
        return (
            layer_model.layers,
            viewport_bounds if not current_bounds else no_update,
            updated_views,
            view_annotations,
        )

    @callback(
        plugin_data_output,
        plugin_data_requested,
        State(
            {"id": get_uuid(LayoutElements.VERIFIED_VIEW_DATA), "tab": ALL},
            "data",
        ),
        State(get_uuid("tabs"), "value"),
        State({"id": get_uuid(LayoutElements.VERIFIED_VIEW_DATA), "tab": ALL}, "id"),
        prevent_initial_call=True,
    )
    def _user_download_data(
        data_requested: bool,
        surface_elements_in_tabs: List[List[Dict]],
        tab_name: str,
        tab_ids: List[dict],
    ) -> Optional[EncodedFile]:
        """Callback for downloading surfaces from the plugin"""
        if not surface_elements_in_tabs or not data_requested:
            return no_update
        index = [x["tab"] for x in tab_ids].index(tab_name)
        surface_elements_in_tab = surface_elements_in_tabs[index]
        surface_bytes = {}
        reals_in_statistics = []
        for s_elem in surface_elements_in_tab:
            if s_elem.get("surf_type") == "diff":
                continue
            surface_address = get_surface_address_from_data(s_elem)
            ensemble = s_elem["ensemble"][0]
            provider = ensemble_surface_providers[ensemble]
            surface = provider.get_surface(surface_address)
            if surface is None:
                continue
            date_str = s_elem["date"][0] if s_elem["date"] else ""
            realizations = s_elem["realizations"]
            mode_str = (
                s_elem["mode"]
                if SurfaceMode(s_elem["mode"]) != SurfaceMode.REALIZATION
                else realizations[0]
            )
            surface_name = (
                f"{s_elem['attribute'][0]}--{s_elem['name'][0]}"
                f"--{date_str}--{mode_str}--{ensemble}.gri"
            )
            if SurfaceMode(s_elem["mode"]) not in [
                SurfaceMode.OBSERVED,
                SurfaceMode.REALIZATION,
            ]:
                reals_in_statistics.append(
                    f"{surface_name},"
                    f"INCLUDED REALIZATIONS: {realizations}, EXCLUDED REALIZATIONS: "
                    f"{[real for real in provider.realizations() if real not in realizations]}"
                )
            byte_stream = io.BytesIO()
            surface.to_file(byte_stream)
            surface_bytes[surface_name] = byte_stream

        with io.BytesIO() as bytes_io:
            with zipfile.ZipFile(bytes_io, "w") as zipped_data:
                for surface_name, surface_byte in surface_bytes.items():
                    zipped_data.writestr(surface_name, surface_byte.getvalue())
                zipped_data.writestr(
                    "statistics.txt",
                    "\n".join(str(real) for real in reals_in_statistics),
                )
            return {
                "filename": "surfaces.zip",
                "content": base64.b64encode(bytes_io.getvalue()).decode("ascii"),
                "mime_type": "application/zip",
            }

    def make_viewport_label(data: dict, tab: str, multi: Optional[str]) -> str:
        """Return text-label for each viewport based on which tab is selected"""
        # For the difference view
        if tab == Tabs.DIFF and data.get("surf_type") == "diff":
            return "Difference Map (View1 - View2)"

        # For the statistics view 'mode' is used as label
        if tab == Tabs.STATS:
            if data["mode"] == SurfaceMode.REALIZATION:
                return f"REAL {data['realizations'][0]}"
            return data["mode"]

        # For the "map per selector" the chosen multi selector is used as label
        if tab == Tabs.SPLIT:
            if multi == "realizations":
                return f"REAL {data['realizations'][0]}"
            return data[multi][0] if multi == "mode" else data[multi]

        return general_label(data)

    def general_label(data: dict) -> str:
        """Create a general map label with all available information"""
        surfaceid = [data["ensemble"][0], data["attribute"][0], data["name"][0]]
        if data["date"]:
            surfaceid.append(data["date"][0])
        if data["mode"] != SurfaceMode.REALIZATION:
            surfaceid.append(data["mode"])
        else:
            surfaceid.append(f"REAL {data['realizations'][0]}")
        return " ".join(surfaceid)

    # pylint: disable=too-many-branches
    def _update_selector_component_properties_from_provider(
        selector_values: List[dict],
        linked_selectors: List[str],
        multi: str,
        multi_in_ctx: bool,
        filtered_realizations: List[int],
    ) -> List[Dict[str, dict]]:
        """Return updated options and values for the different selector components using
        the provider. If current selected value for a selector is in the options it will
        be used as the new value"""
        view_data = []
        for idx, data in enumerate(selector_values):
            if not ("ensemble" in linked_selectors and idx > 0):
                ensembles = list(ensemble_surface_providers.keys())
                ensemble = data.get("ensemble", [])
                ensemble = [ensemble] if isinstance(ensemble, str) else ensemble
                if not ensemble or multi_in_ctx:
                    ensemble = ensembles if multi == "ensemble" else ensembles[:1]

            if not ("attribute" in linked_selectors and idx > 0):
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

            if not ("name" in linked_selectors and idx > 0):
                names = []
                for ens in ensemble:
                    provider = ensemble_surface_providers[ens]
                    for attr in attribute:
                        attr_names = provider.surface_names_for_attribute(attr)
                        names.extend([x for x in attr_names if x not in names])

                name = [x for x in data.get("name", []) if x in names]
                if not name or multi_in_ctx:
                    name = names if multi == "name" else names[:1]

            if not ("date" in linked_selectors and idx > 0):
                dates = []
                for ens in ensemble:
                    provider = ensemble_surface_providers[ens]
                    for attr in attribute:
                        attr_dates = provider.surface_dates_for_attribute(attr)

                        if attr_dates is not None:
                            dates.extend([x for x in attr_dates if x not in dates])

                interval_dates = [x for x in dates if "_" in x]
                dates = [x for x in dates if x not in interval_dates] + interval_dates

                date = [x for x in data.get("date", []) if x in dates]
                if not date or multi_in_ctx:
                    date = dates if multi == "date" else dates[:1]

            if not ("mode" in linked_selectors and idx > 0):
                modes = list(SurfaceMode)
                mode = data.get("mode", SurfaceMode.REALIZATION)

            if not ("realizations" in linked_selectors and idx > 0):
                if mode == SurfaceMode.REALIZATION:
                    real = data.get("realizations", [])
                    if not real or real[0] not in filtered_realizations:
                        real = filtered_realizations[:1]
                else:
                    real = filtered_realizations

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
                        "disabled": mode != SurfaceMode.REALIZATION,
                        "options": filtered_realizations,
                        "multi": mode != SurfaceMode.REALIZATION
                        or multi == "realizations",
                    },
                }
            )

        return view_data

    def _update_color_component_properties(
        values: List[dict],
        links: List[str],
        stored_color_settings: dict,
        reset_color_index: Optional[int],
        color_update_index: Optional[int],
    ) -> List[dict]:
        """Return updated options and values for the different color selector components.
        If previous color settings are found it will be used, or set value to min and max
        surface range unless the user has updated the component through interaction."""
        stored_color_settings = (
            stored_color_settings if stored_color_settings is not None else {}
        )
        colormaps = [color_table["name"] for color_table in color_tables]

        surfids: List[str] = []
        color_data: List[dict] = []
        for idx, data in enumerate(values):
            surfaceid = (
                get_surface_id_for_diff_surf(values)
                if data.get("surf_type") == "diff"
                else get_surface_id_from_data(data)
            )
            # if surfaceid exist in another view use the color settings
            # from that view and disable the color component
            if surfaceid in surfids:
                index_of_first = surfids.index(surfaceid)
                surfids.append(surfaceid)
                view_data = deepcopy(color_data[index_of_first])
                view_data["colormap"].update(disabled=True)
                view_data["color_range"].update(disabled=True)
                color_data.append(view_data)
                continue

            surfids.append(surfaceid)

            use_stored_color = (
                surfaceid in stored_color_settings and not color_update_index == idx
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

    def get_surface_address_from_data(
        data: dict,
    ) -> Union[
        SimulatedSurfaceAddress, ObservedSurfaceAddress, StatisticalSurfaceAddress
    ]:
        """Return the SurfaceAddress based on view selection"""
        has_date = (
            ensemble_surface_providers[data["ensemble"][0]].surface_dates_for_attribute(
                data["attribute"][0]
            )
            is not None
        )

        if data["mode"] == SurfaceMode.REALIZATION:
            return SimulatedSurfaceAddress(
                attribute=data["attribute"][0],
                name=data["name"][0],
                datestr=data["date"][0] if has_date else None,
                realization=int(data["realizations"][0]),
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
            realizations=[int(real) for real in data["realizations"]],
            statistic=data["mode"],
        )

    def publish_and_get_surface_metadata(
        surface_provider: EnsembleSurfaceProvider, surface_address: SurfaceAddress
    ) -> Tuple:
        provider_id: str = surface_provider.provider_id()
        qualified_address = QualifiedSurfaceAddress(provider_id, surface_address)
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
        return surf_meta, surface_server.encode_partial_url(qualified_address)

    def publish_and_get_diff_surface_metadata(
        surface_provider: EnsembleSurfaceProvider,
        surface_address: SurfaceAddress,
        sub_surface_provider: EnsembleSurfaceProvider,
        sub_surface_address: SurfaceAddress,
    ) -> Tuple:
        provider_id: str = surface_provider.provider_id()
        subprovider_id = sub_surface_provider.provider_id()
        qualified_address: Union[QualifiedSurfaceAddress, QualifiedDiffSurfaceAddress]
        qualified_address = QualifiedDiffSurfaceAddress(
            provider_id, surface_address, subprovider_id, sub_surface_address
        )

        surf_meta = surface_server.get_surface_metadata(qualified_address)
        if not surf_meta:
            surface_a = surface_provider.get_surface(address=surface_address)
            surface_b = sub_surface_provider.get_surface(address=sub_surface_address)
            if surface_a is not None and surface_b is not None:
                surface = surface_a - surface_b
            surface_server.publish_surface(qualified_address, surface)
            surf_meta = surface_server.get_surface_metadata(qualified_address)
        return surf_meta, surface_server.encode_partial_url(qualified_address)

    def get_surface_id_from_data(data: dict) -> str:
        """Retrieve surfaceid used for the colorstore"""
        surfaceid = data["attribute"][0] + data["name"][0]
        if data["date"]:
            surfaceid += data["date"][0]
        if data["mode"] == SurfaceMode.STDDEV:
            surfaceid += data["mode"]
        return surfaceid

    def get_surface_id_for_diff_surf(values: List[dict]) -> str:
        """Retrieve surfaceid used for the colorstore, for the diff surface
        this needs to be a combination of the two surfaces subtracted"""
        return get_surface_id_from_data(values[0]) + get_surface_id_from_data(values[1])

    def update_selections_with_multi(values: List[dict], multi: str) -> List[dict]:
        """If a selector has been set as multi, the values selected in that component needs
        to be divided between the views so that there is only one unique value in each
        """
        multi_values = values[0][multi]
        new_values = []
        for val in multi_values:
            updated_values = deepcopy(values[0])
            updated_values[multi] = [val]
            new_values.append(updated_values)
        return new_values

    def attribute_has_date(attribute: str, provider: EnsembleSurfaceProvider) -> bool:
        """Check if an attribute has any dates"""
        return provider.surface_dates_for_attribute(attribute) is not None

    def remove_data_if_not_valid(values: List[dict]) -> List[dict]:
        """Checks if surfaces can be provided from the selections.
        Any invalid selections are removed."""
        updated_values = []
        for data in values:
            surface_address = get_surface_address_from_data(data)
            try:
                provider = ensemble_surface_providers[data["ensemble"][0]]
                surf_meta, _ = publish_and_get_surface_metadata(
                    surface_address=surface_address,
                    surface_provider=provider,
                )
            except ValueError:
                continue
            if not isinstance(
                surf_meta.val_min, np.ma.core.MaskedConstant
            ) and not isinstance(surf_meta.val_max, np.ma.core.MaskedConstant):
                data["surface_range"] = [surf_meta.val_min, surf_meta.val_max]
                updated_values.append(data)

        return updated_values

    def get_surface_metadata_and_image(data: dict) -> Tuple:
        surface_address = get_surface_address_from_data(data)
        provider = ensemble_surface_providers[data["ensemble"][0]]
        return publish_and_get_surface_metadata(
            surface_address=surface_address, surface_provider=provider
        )

    def get_surface_metadata_and_image_for_diff_surface(
        selector_values: List[dict],
    ) -> Tuple:
        surface_address = get_surface_address_from_data(selector_values[0])
        sub_surface_address = get_surface_address_from_data(selector_values[1])
        provider = ensemble_surface_providers[selector_values[0]["ensemble"][0]]
        sub_provider = ensemble_surface_providers[selector_values[1]["ensemble"][0]]
        return publish_and_get_diff_surface_metadata(
            surface_address=surface_address,
            surface_provider=provider,
            sub_surface_address=sub_surface_address,
            sub_surface_provider=sub_provider,
        )

    def add_diff_surface_to_values(selector_values: List[dict]) -> List[dict]:
        surf_meta, _ = get_surface_metadata_and_image_for_diff_surface(selector_values)
        selector_values.append(
            {
                "surface_range": [surf_meta.val_min, surf_meta.val_max],
                "surf_type": "diff",
            }
        )
        return selector_values

    def combine_selector_values_and_name(
        values: list, id_list: list, view: int
    ) -> dict:
        """Combine selector values with selector name for given view"""
        return {
            id_values["selector"]: val
            for val, id_values in zip(values, id_list)
            if id_values["view"] == view
        }


def view_layout(views: int, columns: Optional[int] = None) -> List[int]:
    """Function to set number of rows and columns for the map, if number
    of columns is not specified, a square matrix layout is used"""
    columns = (
        columns
        if columns is not None
        else min([x for x in range(1, 20, 1) if (x * x) >= views])
    )
    rows = math.ceil(views / columns)
    return [rows, columns]
