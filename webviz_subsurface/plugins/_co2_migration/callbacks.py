import json
from typing import Callable, Dict, Optional, List, Tuple
import dash
import pydeck
from dash import callback, Output, Input, State
from dash.exceptions import PreventUpdate
# TODO: tmp?
from webviz_subsurface.plugins._map_viewer_fmu._tmp_well_pick_provider import (
    WellPickProvider,
    WellPickTableColumns,
)
from webviz_subsurface._components.deckgl_map.types.deckgl_props import (
    ColormapLayer,
    FaultPolygonsLayer,
    WellsLayer,
    CustomLayer,
    LayerTypes,
)
from webviz_subsurface._providers import (
    EnsembleFaultPolygonsProvider,
    EnsembleSurfaceProvider,
    FaultPolygonsServer,
    QualifiedSurfaceAddress,
    SimulatedFaultPolygonsAddress,
    SimulatedSurfaceAddress,
    SurfaceAddress,
    SurfaceServer,
)
from ._utils import MapAttribute, FAULT_POLYGON_ATTRIBUTE, realization_paths, parse_polygon_file
from ._co2volume import (generate_co2_volume_figure, generate_co2_time_containment_figure)
from .layout import LayoutElements, LayoutStyle, LayoutLabels


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
    )
    def set_formations(ensemble, prop):
        if ensemble is None:
            return [], None
        # Dates
        surface_provider = ensemble_surface_providers[ensemble]
        # Map
        prop_name = map_attribute_names[MapAttribute(prop)]
        surfaces = surface_name_aliases(surface_provider, prop_name)
        polygons = fault_polygon_aliases(ensemble_fault_polygons_providers[ensemble])
        well_picks = well_pick_names_aliases(well_pick_provider)
        # Formation names
        formations = compile_alias_list(surfaces, well_picks, polygons)
        initial_formation = None
        if len(formations) != 0:
            if "disabled" in formations[0]:
                if any(fmt["value"] == "All" for fmt in formations):
                    initial_formation = "All"
            else:
                initial_formation = formations[0]["value"]
        return formations, initial_formation

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
                    "style": {"writing-mode": "vertical-rl"},
                }
                for i, d in enumerate(date_list)
            }
            initial_date = 0
        return dates, initial_date, date_list

    @callback(
        Output(get_uuid(LayoutElements.DECKGLMAP), "layers"),
        Output(get_uuid(LayoutElements.DECKGLMAP), "bounds"),
        Input(get_uuid(LayoutElements.PROPERTY), "value"),
        Input(get_uuid(LayoutElements.DATEINPUT), "value"),
        Input(get_uuid(LayoutElements.FORMATION_INPUT), "value"),
        Input(get_uuid(LayoutElements.REALIZATIONINPUT), "value"),
        State(get_uuid(LayoutElements.ENSEMBLEINPUT), "value"),
        State(get_uuid(LayoutElements.DATE_STORE), "data"),
    )
    def update_map_attribute(attribute, date, formation, realization, ensemble, date_list):
        if ensemble is None:
            raise PreventUpdate
        if MapAttribute(attribute) != MapAttribute.MIGRATION_TIME and date is None:
            raise PreventUpdate
        date = str(date_list[date])
        # Look up formation aliases
        surface_name = lookup_surface_alias(
            formation,
            ensemble_surface_providers[ensemble],
            map_attribute_names[MapAttribute(attribute)],
        )
        if surface_name is None:
            surface_name = "all"
        polygon_name = lookup_fault_polygon_alias(
            formation, ensemble_fault_polygons_providers[ensemble]
        )
        well_pick_horizon = lookup_well_pick_alias(formation, well_pick_provider)

        layers, viewport_bounds = create_map_layers(
            surface_server=surface_server,
            surface_provider=ensemble_surface_providers[ensemble],
            colormap_address=_derive_colormap_address(surface_name, attribute, date, realization, map_attribute_names),
            fault_polygons_server=fault_polygons_server,
            polygon_provider=ensemble_fault_polygons_providers[ensemble],
            polygon_address=_derive_fault_polygon_address(polygon_name, realization),
            license_boundary_file=license_boundary_file,
            well_pick_provider=well_pick_provider,
            well_pick_horizon=well_pick_horizon,
        )
        return layers, viewport_bounds


def compile_alias_list(*alias_lists):
    alias_sets = [set(s) for s in alias_lists]
    complete = set.intersection(*alias_sets)
    remainder = set.union(*alias_sets) - complete
    options = [{"label": v, "value": v} for v in sorted(list(complete))]
    options += [{"label": "Incomplete data", "value": "", "disabled": True}]
    options += [{"label": v, "value": v} for v in sorted(list(remainder))]
    return options


def surface_name_aliases(surface_provider, prop):
    return [
        s.title()
        for s in surface_provider.surface_names_for_attribute(prop)
    ]


def fault_polygon_aliases(polygon_provider):
    return [
        p.title()
        for p in polygon_provider.fault_polygons_names_for_attribute(FAULT_POLYGON_ATTRIBUTE)
    ]


def well_pick_names_aliases(well_pick_provider):
    if well_pick_provider is None:
        return []
    return [
        p.title()
        for p in well_pick_provider.dframe[WellPickTableColumns.HORIZON].unique()
    ]


def lookup_surface_alias(alias, surface_provider, prop):
    return lookup_formation_alias(alias, surface_provider.surface_names_for_attribute(prop))


def lookup_fault_polygon_alias(alias, polygon_provider):
    return lookup_formation_alias(
        alias, polygon_provider.fault_polygons_names_for_attribute(FAULT_POLYGON_ATTRIBUTE)
    )


def lookup_well_pick_alias(alias, well_pick_provider):
    if well_pick_provider is None:
        return None
    return lookup_formation_alias(
        alias, well_pick_provider.dframe[WellPickTableColumns.HORIZON].unique()
    )


def lookup_formation_alias(alias, names):
    matches = [s for s in names if s.title() == alias]
    if len(matches) == 0:
        return None
    return matches[0]


def create_map_layers(
    surface_server: SurfaceServer,
    surface_provider: EnsembleSurfaceProvider,
    colormap_address: SimulatedSurfaceAddress,
    fault_polygons_server: FaultPolygonsServer,
    polygon_provider: EnsembleFaultPolygonsProvider,
    polygon_address: SimulatedFaultPolygonsAddress,
    license_boundary_file: Optional[str],
    well_pick_provider: Optional[WellPickProvider],
    well_pick_horizon: Optional[str],
) -> Tuple[List[Dict], List[float]]:
    surf_meta, img_url = _publish_and_get_surface_metadata(
        surface_server, surface_provider, colormap_address
    )
    # Update ColormapLayer
    import numpy as np
    # TODO: value_range should perhaps never be masked in the first place? Possible bug
    #  also in MapViewerFMU
    value_range = [
        0.0 if np.ma.is_masked(surf_meta.val_min) else surf_meta.val_min,
        0.0 if np.ma.is_masked(surf_meta.val_max) else surf_meta.val_max,
    ]
    layers = [
        ColormapLayer(
            uuid=LayoutElements.COLORMAPLAYER,
            image=img_url,
            bounds=surf_meta.deckgl_bounds,
            value_range=value_range,
            color_map_range=value_range,
            rotDeg=surf_meta.deckgl_rot_deg,
        ),
    ]
    if polygon_address.name is not None:
        layers.append(FaultPolygonsLayer(
            uuid=LayoutElements.FAULTPOLYGONSLAYER,
            data=fault_polygons_server.encode_partial_url(
                provider_id=polygon_provider.provider_id(),
                fault_polygons_address=polygon_address,
            ),
        ))
    if license_boundary_file is not None:
        layers.append(
            CustomLayer(
                layer_type=LayerTypes.FAULTPOLYGONS,
                uuid=LayoutElements.LICENSEBOUNDARYLAYER,
                name=LayoutLabels.LICENSE_BOUNDARY_LAYER,
                data=parse_polygon_file(license_boundary_file)
            )
        )
    if well_pick_provider is not None:
        # Need to cast to dict. Possible bug when passing geojson.FeatureCollection via
        # WellsLayer.__init__
        layers.append(
            WellsLayer(
                uuid=LayoutElements.WELLPICKSLAYER,
                data=dict(
                    well_pick_provider.get_geojson(
                        well_pick_provider.well_names(), well_pick_horizon
                    )
                ),
            )
        )
    # View-port
    viewport_bounds = [
        surf_meta.x_min,
        surf_meta.y_min,
        surf_meta.x_max,
        surf_meta.y_max,
    ]
    # Convert layers to dictionaries
    layers = [json.loads(lay.to_json()) for lay in layers]
    return layers, viewport_bounds


def _derive_colormap_address(
    surface_name: str,
    attribute: str,
    date: Optional[str],
    realization: int,
    map_attribute_names: Dict[MapAttribute, str]
):
    attribute = MapAttribute(attribute)
    date = None if attribute == MapAttribute.MIGRATION_TIME else date
    return SimulatedSurfaceAddress(
        attribute=map_attribute_names[attribute],
        name=surface_name,
        datestr=date,
        realization=realization
    )


def _derive_fault_polygon_address(polygon_name, realization):
    return SimulatedFaultPolygonsAddress(
        attribute=FAULT_POLYGON_ATTRIBUTE,
        name=polygon_name,
        realization=realization,
    )


def _publish_and_get_surface_metadata(
    surface_server: SurfaceServer,
    surface_provider: EnsembleSurfaceProvider,
    surface_address: SurfaceAddress,
):
    # TODO: Nearly direct copy from MapViewerFMU
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
