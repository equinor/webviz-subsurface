from dataclasses import dataclass
from typing import Callable, Dict, Optional, List, Tuple, Set, Union

import geojson
import numpy as np
import dash
from dash import callback, Output, Input, State
from dash.exceptions import PreventUpdate
from webviz_subsurface._providers.ensemble_surface_provider.ensemble_surface_provider import (
    SurfaceStatistic, SurfaceAddress
)
# TODO: tmp?
from webviz_subsurface.plugins._map_viewer_fmu._tmp_well_pick_provider import (
    WellPickProvider,
)
from webviz_subsurface._providers import (
    EnsembleFaultPolygonsProvider,
    EnsembleSurfaceProvider,
    FaultPolygonsServer,
    SimulatedFaultPolygonsAddress,
    SimulatedSurfaceAddress,
    SurfaceServer,
    SurfaceMeta,
    StatisticalSurfaceAddress,
)
from . import _plume_extent
from ._formation_alias import (
    compile_alias_list,
    surface_name_aliases,
    fault_polygon_aliases,
    well_pick_names_aliases,
    lookup_surface_alias,
    lookup_fault_polygon_alias,
    lookup_well_pick_alias,
)
from ._surface_publishing import (
    FrequencySurfaceAddress,
    publish_and_get_surface_metadata,
)
from ._utils import MapAttribute, FAULT_POLYGON_ATTRIBUTE, realization_paths, parse_polygon_file
from ._co2volume import (generate_co2_volume_figure, generate_co2_time_containment_figure)
from .layout import LayoutElements, LayoutStyle, LayoutLabels


@dataclass
class _SurfaceData:
    color_map_range: Tuple[float, float]
    color_map_name: str
    value_range: Tuple[float, float]
    meta_data: SurfaceMeta
    img_url: str

    @staticmethod
    def from_server(
        server: SurfaceServer,
        provider: EnsembleSurfaceProvider,
        address: Union[SurfaceAddress, FrequencySurfaceAddress],
        color_map_range: Optional[Tuple[float, float]],
        color_map_name: str,
    ):
        surf_meta, img_url = publish_and_get_surface_metadata(server, provider, address)
        value_range = (
            0.0 if np.ma.is_masked(surf_meta.val_min) else surf_meta.val_min,
            0.0 if np.ma.is_masked(surf_meta.val_max) else surf_meta.val_max,
        )
        color_map_range = (
            value_range[0] if color_map_range[0] is None else color_map_range[0],
            value_range[1] if color_map_range[1] is None else color_map_range[1],
        )
        return _SurfaceData(
            color_map_range, color_map_name, value_range, surf_meta, img_url
        )


def plugin_callbacks(
    get_uuid: Callable,
    ensemble_paths: Dict[str, str],
    ensemble_surface_providers: Dict[str, EnsembleSurfaceProvider],
    surface_server: SurfaceServer,
    ensemble_fault_polygons_providers: Dict[str, EnsembleFaultPolygonsProvider],
    fault_polygons_server: FaultPolygonsServer,
    license_boundary_file: Optional[str],
    well_pick_provider: Optional[WellPickProvider],
    map_attribute_names: Dict[MapAttribute, str],
    formation_aliases: List[Set[str]],
):
    @callback(
        Output(get_uuid(LayoutElements.REALIZATIONINPUT), "options"),
        Output(get_uuid(LayoutElements.REALIZATIONINPUT), "value"),
        Output(get_uuid(LayoutElements.ENSEMBLEBARPLOT), "figure"),
        Output(get_uuid(LayoutElements.ENSEMBLETIMELEAKPLOT), "figure"),
        Input(get_uuid(LayoutElements.ENSEMBLEINPUT), "value"),
    )
    def set_realizations(ensemble):
        rz_paths = realization_paths(ensemble_paths[ensemble])
        realizations = [
            dict(label=r, value=r)
            for r in sorted(rz_paths.keys())
        ]
        fig0 = generate_co2_volume_figure(
            rz_paths, LayoutStyle.ENSEMBLE_PLOT_HEIGHT, LayoutStyle.ENSEMBLE_PLOT_WIDTH
        )
        fig1 = generate_co2_time_containment_figure(
            rz_paths, LayoutStyle.ENSEMBLE_PLOT_HEIGHT, LayoutStyle.ENSEMBLE_PLOT_WIDTH
        )
        return realizations, realizations[0]["value"], fig0, fig1

    @callback(
        Output(get_uuid(LayoutElements.FORMATION_INPUT), 'options'),
        Output(get_uuid(LayoutElements.FORMATION_INPUT), 'value'),
        State(get_uuid(LayoutElements.ENSEMBLEINPUT), 'value'),
        Input(get_uuid(LayoutElements.PROPERTY), 'value'),
        State(get_uuid(LayoutElements.FORMATION_INPUT), 'value'),
    )
    def set_formations(ensemble, prop, current_value):
        if ensemble is None:
            return [], None
        surface_provider = ensemble_surface_providers[ensemble]
        # Map
        prop_name = _property_origin(MapAttribute(prop), map_attribute_names)
        surfaces = surface_name_aliases(surface_provider, prop_name)
        polygons = fault_polygon_aliases(ensemble_fault_polygons_providers[ensemble])
        well_picks = well_pick_names_aliases(well_pick_provider)
        # Formation names
        formations = compile_alias_list(formation_aliases, surfaces, well_picks, polygons)
        picked_formation = None
        if len(formations) != 0:
            if any(fmt["value"] == current_value for fmt in formations):
                picked_formation = dash.no_update
            elif "disabled" in formations[0]:
                if any(fmt["value"] == "all" for fmt in formations):
                    picked_formation = "all"
            else:
                picked_formation = formations[0]["value"]
        return formations, picked_formation

    @callback(
        Output(get_uuid(LayoutElements.DATEINPUT), 'marks'),
        Output(get_uuid(LayoutElements.DATEINPUT), 'value'),
        Output(get_uuid(LayoutElements.DATE_STORE), "data"),
        Input(get_uuid(LayoutElements.ENSEMBLEINPUT), 'value'),
    )
    def set_dates(ensemble):
        if ensemble is None:
            return [], None, []
        # Dates
        surface_provider = ensemble_surface_providers[ensemble]
        att_name = map_attribute_names[MapAttribute.MAX_SATURATION]
        date_list = surface_provider.surface_dates_for_attribute(att_name)
        if date_list is None:
            dates = {}
            initial_date = dash.no_update
        else:
            dates = {
                # Regarding tooltips: https://github.com/plotly/dash/issues/1846
                i: {
                    "label": f"{d[:4]}.{d[4:6]}.{d[6:]}",
                    "style": {"writingMode": "vertical-rl"},
                }
                for i, d in enumerate(date_list)
            }
            initial_date = max(dates.keys())
        return dates, initial_date, date_list

    @callback(
        Output(get_uuid(LayoutElements.COLOR_RANGE_STORE), "data"),
        Output(get_uuid(LayoutElements.COLOR_RANGE_MIN_VALUE), "disabled"),
        Output(get_uuid(LayoutElements.COLOR_RANGE_MAX_VALUE), "disabled"),
        Input(get_uuid(LayoutElements.COLOR_RANGE_MIN_AUTO), "value"),
        Input(get_uuid(LayoutElements.COLOR_RANGE_MIN_VALUE), "value"),
        Input(get_uuid(LayoutElements.COLOR_RANGE_MAX_AUTO), "value"),
        Input(get_uuid(LayoutElements.COLOR_RANGE_MAX_VALUE), "value"),
    )
    def set_color_range_data(min_auto, min_val, max_auto, max_val):
        return (
            [
                min_val if len(min_auto) == 0 else None,
                max_val if len(max_auto) == 0 else None,
            ],
            len(min_auto) == 1,
            len(max_auto) == 1,
        )

    @callback(
        Output(get_uuid(LayoutElements.DECKGLMAP), "layers"),
        Output(get_uuid(LayoutElements.DECKGLMAP), "bounds"),
        Input(get_uuid(LayoutElements.PROPERTY), "value"),
        Input(get_uuid(LayoutElements.DATEINPUT), "value"),
        Input(get_uuid(LayoutElements.FORMATION_INPUT), "value"),
        Input(get_uuid(LayoutElements.REALIZATIONINPUT), "value"),
        Input(get_uuid(LayoutElements.STATISTIC_INPUT), "value"),
        Input(get_uuid(LayoutElements.COLORMAP_INPUT), "value"),
        Input(get_uuid(LayoutElements.COLOR_RANGE_STORE), "data"),
        Input(get_uuid(LayoutElements.CONTOUR_PROPERTY), "value"),
        Input(get_uuid(LayoutElements.CONTOUR_THRESHOLD), "value"),
        Input(get_uuid(LayoutElements.CONTOUR_SMOOTHING), "value"),
        State(get_uuid(LayoutElements.ENSEMBLEINPUT), "value"),
        State(get_uuid(LayoutElements.DATE_STORE), "data"),
        State(get_uuid(LayoutElements.DECKGLMAP), "bounds"),
    )
    def update_map_attribute(
        attribute,
        date,
        formation,
        realization,
        statistic,
        color_map_name,
        color_map_range,
        contour_property,
        contour_threshold,
        contour_smoothing,
        ensemble,
        date_list,
        current_bounds,
    ):
        attribute = MapAttribute(attribute)
        if isinstance(realization, int):
            realization = [realization]
        elif len(realization) == 0:
            raise PreventUpdate
        if ensemble is None:
            raise PreventUpdate
        if attribute != MapAttribute.MIGRATION_TIME and date is None:
            raise PreventUpdate
        date = str(date_list[date])
        # Look up formation aliases
        surface_name = lookup_surface_alias(
            formation_aliases,
            formation,
            ensemble_surface_providers[ensemble],
            _property_origin(attribute, map_attribute_names),
        )
        polygon_name = lookup_fault_polygon_alias(
            formation_aliases, formation, ensemble_fault_polygons_providers[ensemble]
        )
        well_pick_horizon = lookup_well_pick_alias(
            formation_aliases, formation, well_pick_provider
        )
        # Surface
        if surface_name is None:
            surf_data = None
        elif len(realization) == 0:
            surf_data = None
        elif len(realization) > 1 and statistic is None:
            surf_data = None
        else:
            surf_data = _SurfaceData.from_server(
                server=surface_server,
                provider=ensemble_surface_providers[ensemble],
                address=_derive_surface_address(
                    surface_name,
                    attribute,
                    date,
                    realization,
                    map_attribute_names,
                    statistic,
                ),
                color_map_range=color_map_range,
                color_map_name=color_map_name,
            )
        # Plume polygon
        if (
            contour_property is not None
            and len(realization) > 0
            and contour_threshold is not None
            and contour_threshold > 0
        ):
            plume_polygon = _get_plume_polygon(
                ensemble_surface_providers[ensemble],
                realization,
                surface_name,
                contour_property,
                date,
                len(contour_smoothing) > 0,
                contour_threshold,
            )
        else:
            plume_polygon = None
        # Create layers and view bounds
        layers, viewport_bounds = create_map_layers(
            surface_data=surf_data,
            fault_polygon_url=_extract_fault_polygon_url(
                server=fault_polygons_server,
                provider=ensemble_fault_polygons_providers[ensemble],
                polygon_name=polygon_name,
                realization=realization,
            ),
            license_boundary_file=license_boundary_file,
            well_pick_provider=well_pick_provider,
            well_pick_horizon=well_pick_horizon,
            plume_extent_data=plume_polygon,
        )
        if tuple(current_bounds) != LayoutStyle.INITIAL_BOUNDS:
            viewport_bounds = dash.no_update
        return layers, viewport_bounds


def create_map_layers(
    surface_data: Optional[_SurfaceData],
    fault_polygon_url: Optional[str],
    license_boundary_file: Optional[str],
    well_pick_provider: Optional[WellPickProvider],
    well_pick_horizon: Optional[str],
    plume_extent_data: Optional[geojson.FeatureCollection],
) -> Tuple[List[Dict], List[float]]:
    layers = []
    viewport_bounds = dash.no_update
    if surface_data is not None:
        # Update ColormapLayer
        layers.append({
            "@@type": "ColormapLayer",
            "name": "Property",
            "id": LayoutElements.COLORMAPLAYER,
            "image": surface_data.img_url,
            "bounds": surface_data.meta_data.deckgl_bounds,
            "valueRange": surface_data.value_range,
            "colorMapRange": surface_data.color_map_range,
            "colorMapName": surface_data.color_map_name,
            "rotDeg": surface_data.meta_data.deckgl_rot_deg,
        })
        viewport_bounds = [
            surface_data.meta_data.x_min,
            surface_data.meta_data.y_min,
            surface_data.meta_data.x_max,
            surface_data.meta_data.y_max,
        ]
    if fault_polygon_url is not None:
        layers.append({
            "@@type": "FaultPolygonsLayer",
            "name": "Fault Polygons",
            "id": LayoutElements.FAULTPOLYGONSLAYER,
            "data": fault_polygon_url,
        })
    if license_boundary_file is not None:
        layers.append({
            "@@type": "FaultPolygonsLayer",
            "name": LayoutLabels.LICENSE_BOUNDARY_LAYER,
            "id": LayoutElements.LICENSEBOUNDARYLAYER,
            "data": parse_polygon_file(license_boundary_file),
        })
    if well_pick_provider is not None:
        # Need to cast to dict. Possible bug when passing geojson.FeatureCollection via
        # WellsLayer.__init__
        layers.append({
            "@@type": "GeoJsonLayer",
            "name": "Well Picks",
            "id": LayoutElements.WELLPICKSLAYER,
            "data": dict(
                well_pick_provider.get_geojson(
                    well_pick_provider.well_names(), well_pick_horizon
                )
            ),
        })
    if plume_extent_data is not None:
        layers.append({
            "@@type": "GeoJsonLayer",
            "name": "Plume Contours",
            "id": LayoutElements.PLUME_POLYGON_LAYER,
            "data": dict(plume_extent_data),
            "lineWidthMinPixels": 2,
            "getLineColor": [150, 150, 150, 255],
        })
    return layers, viewport_bounds


def _property_origin(attribute: MapAttribute, map_attribute_names: Dict[MapAttribute, str]):
    if attribute in map_attribute_names:
        return map_attribute_names[attribute]
    elif attribute == MapAttribute.SGAS_PLUME:
        return map_attribute_names[MapAttribute.MAX_SATURATION]
    elif attribute == MapAttribute.AMFG_PLUME:
        return map_attribute_names[MapAttribute.MAX_AMFG]
    else:
        raise AssertionError(f"No origin defined for property: {attribute}")


def _extract_fault_polygon_url(
    server: FaultPolygonsServer,
    provider: EnsembleFaultPolygonsProvider,
    polygon_name: Optional[str],
    realization: List[int],
) -> Optional[str]:
    if polygon_name is None:
        return None
    if len(realization) == 0:
        return None
    # This always returns the url corresponding to the first realization
    address = _derive_fault_polygon_address(polygon_name, realization[0])
    return server.encode_partial_url(
        provider_id=provider.provider_id(),
        fault_polygons_address=address,
    )


def _derive_surface_address(
    surface_name: str,
    attribute: MapAttribute,
    date: Optional[str],
    realization: List[int],
    map_attribute_names: Dict[MapAttribute, str],
    statistic: str,
):
    date = None if attribute == MapAttribute.MIGRATION_TIME else date
    if attribute in (MapAttribute.SGAS_PLUME, MapAttribute.AMFG_PLUME):
        return FrequencySurfaceAddress(
            name=surface_name,
            datestr=date,
            realizations=realization,
            basis_attribute=(
                map_attribute_names[MapAttribute.MAX_SATURATION]
                if attribute == MapAttribute.SGAS_PLUME
                else map_attribute_names[MapAttribute.MAX_AMFG]
            ),
            threshold=.0001,
            smoothing=10.0,
        )
    elif len(realization) == 1:
        return SimulatedSurfaceAddress(
            attribute=map_attribute_names[attribute],
            name=surface_name,
            datestr=date,
            realization=realization[0],
        )
    else:
        return StatisticalSurfaceAddress(
            attribute=map_attribute_names[attribute],
            name=surface_name,
            datestr=date,
            statistic=SurfaceStatistic(statistic),
            realizations=realization,
        )


def _derive_fault_polygon_address(polygon_name, realization):
    return SimulatedFaultPolygonsAddress(
        attribute=FAULT_POLYGON_ATTRIBUTE,
        name=polygon_name,
        realization=realization,
    )


def _get_plume_polygon(
    surface_provider: EnsembleSurfaceProvider,
    realizations: List[int],
    surface_name: str,
    surface_attribute: str,
    datestr: str,
    smoothing: bool,
    threshold: float,
):
    surfaces = [
        surface_provider.get_surface(SimulatedSurfaceAddress(
            attribute=surface_attribute,
            name=surface_name,
            datestr=datestr,
            realization=r,
        ))
        for r in realizations
    ]
    return _plume_extent.plume_polygon(
        surfaces,
        threshold,
        smoothing=10.0 if smoothing else 0.0,
        simplify_factor=1.2 if smoothing else 0.0,
    )
