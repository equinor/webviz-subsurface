import warnings
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import geojson
import numpy as np
import plotly.graph_objects as go
import webviz_subsurface_components as wsc

from webviz_subsurface._providers import (
    EnsembleSurfaceProvider,
    EnsembleTableProvider,
    SimulatedSurfaceAddress,
    StatisticalSurfaceAddress,
    SurfaceAddress,
    SurfaceImageMeta,
    SurfaceImageServer,
)
from webviz_subsurface._providers.ensemble_surface_provider.ensemble_surface_provider import (
    SurfaceStatistic,
)
from webviz_subsurface._utils.webvizstore_functions import read_csv
from webviz_subsurface.plugins._co2_leakage._utilities import plume_extent
from webviz_subsurface.plugins._co2_leakage._utilities.co2volume import (
    generate_co2_time_containment_figure,
    generate_co2_time_containment_one_realization_figure,
    generate_co2_volume_figure,
)
from webviz_subsurface.plugins._co2_leakage._utilities.generic import (
    Co2MassScale,
    Co2VolumeScale,
    LayoutLabels,
    MapAttribute,
)
from webviz_subsurface.plugins._co2_leakage._utilities.summary_graphs import (
    generate_summary_figure,
)
from webviz_subsurface.plugins._co2_leakage._utilities.surface_publishing import (
    TruncatedSurfaceAddress,
    publish_and_get_surface_metadata,
)
from webviz_subsurface.plugins._map_viewer_fmu._tmp_well_pick_provider import (
    WellPickProvider,
)


def property_origin(
    attribute: MapAttribute, map_attribute_names: Dict[MapAttribute, str]
) -> str:
    if attribute in map_attribute_names:
        return map_attribute_names[attribute]
    if attribute == MapAttribute.SGAS_PLUME:
        return map_attribute_names[MapAttribute.MAX_SGAS]
    if attribute == MapAttribute.AMFG_PLUME:
        return map_attribute_names[MapAttribute.MAX_AMFG]
    raise AssertionError(f"No origin defined for property: {attribute}")


@dataclass
class SurfaceData:
    readable_name: str
    color_map_range: Tuple[Optional[float], Optional[float]]
    color_map_name: str
    value_range: Tuple[float, float]
    meta_data: SurfaceImageMeta
    img_url: str

    @staticmethod
    def from_server(
        server: SurfaceImageServer,
        provider: EnsembleSurfaceProvider,
        address: Union[SurfaceAddress, TruncatedSurfaceAddress],
        color_map_range: Tuple[Optional[float], Optional[float]],
        color_map_name: str,
        readable_name_: str,
        visualization_threshold: float,
    ) -> "SurfaceData":
        surf_meta, img_url, summed_mass = publish_and_get_surface_metadata(
            server,
            provider,
            address,
            visualization_threshold,
        )
        assert surf_meta is not None  # Should not occur
        value_range = (
            0.0 if np.ma.is_masked(surf_meta.val_min) else surf_meta.val_min,
            0.0 if np.ma.is_masked(surf_meta.val_max) else surf_meta.val_max,
        )
        color_map_range = (
            value_range[0] if color_map_range[0] is None else color_map_range[0],
            value_range[1] if color_map_range[1] is None else color_map_range[1],
        )
        return (
            SurfaceData(
                readable_name_,
                color_map_range,
                color_map_name,
                value_range,
                surf_meta,
                img_url,
            ),
            summed_mass,
        )


def derive_surface_address(
    surface_name: str,
    attribute: MapAttribute,
    date: Optional[str],
    realization: List[int],
    map_attribute_names: Dict[MapAttribute, str],
    statistic: str,
    contour_data: Optional[Dict[str, Any]],
) -> Union[SurfaceAddress, TruncatedSurfaceAddress]:
    if attribute in (MapAttribute.SGAS_PLUME, MapAttribute.AMFG_PLUME):
        assert date is not None
        basis = (
            MapAttribute.MAX_SGAS
            if attribute == MapAttribute.SGAS_PLUME
            else MapAttribute.MAX_AMFG
        )
        return TruncatedSurfaceAddress(
            name=surface_name,
            datestr=date,
            realizations=realization,
            basis_attribute=map_attribute_names[basis],
            threshold=contour_data["threshold"] if contour_data else 0.0,
            smoothing=contour_data["smoothing"] if contour_data else 0.0,
        )
    date = None if attribute == MapAttribute.MIGRATION_TIME else date
    if len(realization) == 1:
        return SimulatedSurfaceAddress(
            attribute=map_attribute_names[attribute],
            name=surface_name,
            datestr=date,
            realization=realization[0],
        )
    return StatisticalSurfaceAddress(
        attribute=map_attribute_names[attribute],
        name=surface_name,
        datestr=date,
        statistic=SurfaceStatistic(statistic),
        realizations=realization,
    )


def readable_name(attribute: MapAttribute) -> str:
    unit = ""
    if attribute == MapAttribute.MIGRATION_TIME:
        unit = " [year]"
    elif attribute in (MapAttribute.AMFG_PLUME, MapAttribute.SGAS_PLUME):
        unit = " [# real.]"
    return f"{attribute.value}{unit}"


def get_plume_polygon(
    surface_provider: EnsembleSurfaceProvider,
    realizations: List[int],
    surface_name: str,
    datestr: str,
    contour_data: Dict[str, Any],
) -> Optional[geojson.FeatureCollection]:
    surface_attribute = contour_data["property"]
    threshold = contour_data["threshold"]
    smoothing = contour_data["smoothing"]
    if (
        surface_attribute is None
        or len(realizations) == 0
        or threshold is None
        or threshold <= 0
    ):
        return None
    surfaces = [
        surface_provider.get_surface(
            SimulatedSurfaceAddress(
                attribute=surface_attribute,
                name=surface_name,
                datestr=datestr,
                realization=r,
            )
        )
        for r in realizations
    ]
    surfaces = [s for s in surfaces if s is not None]
    if len(surfaces) == 0:
        return None
    return plume_extent.plume_polygons(
        surfaces,
        threshold,
        smoothing=smoothing,
        simplify_factor=0.12 * smoothing,  # Experimental
    )


def _find_legend_title(attribute: MapAttribute):
    if attribute == MapAttribute.MIGRATION_TIME:
        return "years"
    elif attribute in [MapAttribute.MASS, MapAttribute.DISSOLVED, MapAttribute.FREE]:
        return "kg"
    return ""


def create_map_annotations(
    formation: str,
    surface_data: Optional[SurfaceData],
    colortables: List[Dict[str, Any]],
    attribute: MapAttribute,
) -> List[wsc.ViewAnnotation]:
    annotations = []
    if surface_data is not None:
        annotations.append(
            wsc.ViewAnnotation(
                id="1_view",
                children=[
                    wsc.WebVizColorLegend(
                        title=_find_legend_title(attribute),
                        min=surface_data.color_map_range[0],
                        max=surface_data.color_map_range[1],
                        colorName=surface_data.color_map_name,
                        cssLegendStyles={"top": "0", "right": "0"},
                        openColorSelector=False,
                        legendScaleSize=0.1,
                        legendFontSize=30,
                        colorTables=colortables,
                    ),
                    wsc.ViewFooter(children=formation),
                ],
            )
        )
    return annotations


def create_map_viewports() -> Dict:
    return {
        "layout": [1, 1],
        "viewports": [
            {
                "id": "1_view",
                "show3D": False,
                "isSync": True,
                "layerIds": [
                    "colormap-layer",
                    "fault-polygons-layer",
                    "license-boundary-layer",
                    "hazardous-boundary-layer",
                    "well-picks-layer",
                    "plume-polygon-layer",
                ],
            }
        ],
    }


# pylint: disable=too-many-arguments
def create_map_layers(
    formation: str,
    surface_data: Optional[SurfaceData],
    fault_polygon_url: Optional[str],
    file_containment_boundary: Optional[str],
    file_hazardous_boundary: Optional[str],
    well_pick_provider: Optional[WellPickProvider],
    plume_extent_data: Optional[geojson.FeatureCollection],
    options_dialog_options: List[int],
    selected_wells: List[str],
) -> List[Dict]:
    layers = []
    if surface_data is not None:
        # Update ColormapLayer
        layers.append(
            {
                "@@type": "ColormapLayer",
                "name": surface_data.readable_name,
                "id": "colormap-layer",
                "image": surface_data.img_url,
                "bounds": surface_data.meta_data.deckgl_bounds,
                "valueRange": surface_data.value_range,
                "colorMapRange": surface_data.color_map_range,
                "colorMapName": surface_data.color_map_name,
                "rotDeg": surface_data.meta_data.deckgl_rot_deg,
            }
        )

    if (
        fault_polygon_url is not None
        and LayoutLabels.SHOW_FAULTPOLYGONS in options_dialog_options
    ):
        layers.append(
            {
                "@@type": "FaultPolygonsLayer",
                "name": "Fault Polygons",
                "id": "fault-polygons-layer",
                "data": fault_polygon_url,
            }
        )
    if (
        file_containment_boundary is not None
        and LayoutLabels.SHOW_CONTAINMENT_POLYGON in options_dialog_options
    ):
        layers.append(
            {
                "@@type": "GeoJsonLayer",
                "name": "Containment Polygon",
                "id": "license-boundary-layer",
                "data": _parse_polygon_file(file_containment_boundary),
                "stroked": False,
                "getFillColor": [0, 172, 0, 120],
                "visible": True,
            }
        )
    if (
        file_hazardous_boundary is not None
        and LayoutLabels.SHOW_HAZARDOUS_POLYGON in options_dialog_options
    ):
        layers.append(
            {
                "@@type": "GeoJsonLayer",
                "name": "Hazardous Polygon",
                "id": "hazardous-boundary-layer",
                "data": _parse_polygon_file(file_hazardous_boundary),
                "stroked": False,
                "getFillColor": [200, 0, 0, 120],
                "visible": True,
            }
        )
    if (
        well_pick_provider is not None
        and LayoutLabels.SHOW_WELLS in options_dialog_options
    ):
        well_data = dict(well_pick_provider.get_geojson(selected_wells, formation))
        if "features" in well_data:
            if len(well_data["features"]) == 0:
                warnings.warn(
                    f'Formation name "{formation}" not found in well picks file.'
                )
            for i in range(len(well_data["features"])):
                current_attribute = well_data["features"][i]["properties"]["attribute"]
                well_data["features"][i]["properties"]["attribute"] = (
                    " " + current_attribute
                )
        layers.append(
            {
                "@@type": "GeoJsonLayer",
                "name": "Well Picks",
                "id": "well-picks-layer",
                "data": well_data,
                "visible": True,
                "getText": "@@=properties.attribute",
                "getTextSize": 12,
                "getTextAnchor": "start",
                "pointType": "circle+text",
                "lineWidthMinPixels": 2,
                "pointRadiusMinPixels": 2,
                "pickable": True,
                "parameters": {"depthTest": False},
            }
        )
    if plume_extent_data is not None:
        layers.append(
            {
                "@@type": "GeoJsonLayer",
                "name": "Plume Contours",
                "id": "plume-polygon-layer",
                "data": dict(plume_extent_data),
                "lineWidthMinPixels": 2,
                "getLineColor": [150, 150, 150, 255],
            }
        )
    return layers


def generate_containment_figures(
    table_provider: EnsembleTableProvider,
    co2_scale: Union[Co2MassScale, Co2VolumeScale],
    realization: int,
    y_limits: List[Optional[float]],
    zone: Optional[str],
    zones: Optional[List[str]],
) -> Tuple[go.Figure, go.Figure, go.Figure]:
    try:
        fig0 = generate_co2_volume_figure(
            table_provider,
            table_provider.realizations(),
            co2_scale,
            zone,
            zones,
        )
        fig1 = generate_co2_time_containment_figure(
            table_provider,
            table_provider.realizations(),
            co2_scale,
            zone,
            zones,
        )
        fig2 = generate_co2_time_containment_one_realization_figure(
            table_provider, co2_scale, realization, y_limits, zone, zones
        )
    except KeyError as exc:
        warnings.warn(f"Could not generate CO2 figures: {exc}")
        raise exc
    return fig0, fig1, fig2


def generate_unsmry_figures(
    table_provider_unsmry: EnsembleTableProvider,
    co2_mass_scale: Union[Co2MassScale, Co2VolumeScale],
    table_provider_containment: EnsembleTableProvider,
) -> Tuple[go.Figure]:
    return (
        generate_summary_figure(
            table_provider_unsmry,
            table_provider_unsmry.realizations(),
            co2_mass_scale,
            table_provider_containment,
            table_provider_containment.realizations(),
        ),
    )


def _parse_polygon_file(filename: str) -> Dict[str, Any]:
    df = read_csv(filename)
    if "x" in df.columns:
        xyz = df[["x", "y"]].values
    elif "X_UTME" in df.columns:
        if "POLY_ID" in df.columns:
            xyz = [gf[["X_UTME", "Y_UTMN"]].values for _, gf in df.groupby("POLY_ID")]
        else:
            xyz = df[["X_UTME", "Y_UTMN"]].values
    else:
        # Attempt to use the first two columns as the x and y coordinates
        xyz = df.values[:, :2]
    if isinstance(xyz, list):
        poly_type = "MultiPolygon"
        coords = [[arr.tolist()] for arr in xyz]
    else:
        poly_type = "Polygon"
        coords = [xyz.tolist()]
    as_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": poly_type,
                    "coordinates": coords,
                },
            }
        ],
    }
    return as_geojson
