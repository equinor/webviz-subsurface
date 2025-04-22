import warnings
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import geojson
import numpy as np
import plotly.graph_objects as go
import webviz_subsurface_components as wsc
from dash import no_update
from flask_caching import Cache

from webviz_subsurface._providers import (
    EnsembleSurfaceProvider,
    SimulatedSurfaceAddress,
    StatisticalSurfaceAddress,
    SurfaceAddress,
    SurfaceImageMeta,
    SurfaceImageServer,
)
from webviz_subsurface._providers.ensemble_surface_provider.ensemble_surface_provider import (
    SurfaceStatistic,
)
from webviz_subsurface.plugins._co2_leakage._types import LegendData
from webviz_subsurface.plugins._co2_leakage._utilities import plume_extent
from webviz_subsurface.plugins._co2_leakage._utilities.co2volume import (
    generate_co2_box_plot_figure,
    generate_co2_statistics_figure,
    generate_co2_time_containment_figure,
    generate_co2_time_containment_one_realization_figure,
    generate_co2_volume_figure,
)
from webviz_subsurface.plugins._co2_leakage._utilities.containment_data_provider import (
    ContainmentDataProvider,
)
from webviz_subsurface.plugins._co2_leakage._utilities.containment_info import (
    ContainmentInfo,
    StatisticsTabOption,
)
from webviz_subsurface.plugins._co2_leakage._utilities.ensemble_well_picks import (
    EnsembleWellPicks,
)
from webviz_subsurface.plugins._co2_leakage._utilities.generic import (
    Co2MassScale,
    Co2VolumeScale,
    FilteredMapAttribute,
    GraphSource,
    LayoutLabels,
    MapAttribute,
    MapGroup,
    MapType,
    MenuOptions,
)
from webviz_subsurface.plugins._co2_leakage._utilities.summary_graphs import (
    generate_summary_figure,
)
from webviz_subsurface.plugins._co2_leakage._utilities.surface_publishing import (
    TruncatedSurfaceAddress,
    publish_and_get_surface_metadata,
)
from webviz_subsurface.plugins._co2_leakage._utilities.unsmry_data_provider import (
    UnsmryDataProvider,
)


def property_origin(
    attribute: MapAttribute, map_attribute_names: FilteredMapAttribute
) -> str:
    if MapType[MapAttribute(attribute).name].value == "PLUME":
        return [
            map_attribute_names[attr]
            for attr in MapAttribute
            if MapGroup[attr.name].value == MapGroup[MapAttribute(attribute).name].value
            and MapType[attr.name] == "MAX"
        ][0]
    return map_attribute_names[attribute]


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
        visualization_info: Dict[str, Any],
        map_attribute_names: FilteredMapAttribute,
    ) -> Tuple[Any, Optional[Any]]:
        surf_meta, img_url, summed_mass = publish_and_get_surface_metadata(
            server,
            provider,
            address,
            visualization_info,
            map_attribute_names,
        )
        if surf_meta is None:  # Surface file does not exist
            return None, None
        assert isinstance(img_url, str)
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


def extract_legendonly(figure: go.Figure) -> List[str]:
    # Finds the names OR legendgroup of the traces in the figure which have their
    # visibility set to "legendonly". In the figure, these traces are toggled OFF in the
    # legend.
    return [
        d.get("legendgroup", d.get("name"))
        for d in figure["data"]
        if d.get("visible", "") == "legendonly"
    ]


def derive_surface_address(
    surface_name: str,
    attribute: MapAttribute,
    date: Optional[str],
    realization: List[int],
    map_attribute_names: FilteredMapAttribute,
    statistic: str,
    contour_data: Optional[Dict[str, Any]],
) -> Union[SurfaceAddress, TruncatedSurfaceAddress]:
    if MapType[MapAttribute(attribute).name].value == "PLUME":
        max_attr_name = f"MAX_{MapGroup[MapAttribute(attribute).name]}"
        assert date is not None
        basis = getattr(MapAttribute, max_attr_name)
        return TruncatedSurfaceAddress(
            name=surface_name,
            datestr=date,
            realizations=realization,
            basis_attribute=map_attribute_names[basis],
            threshold=contour_data["threshold"] if contour_data else 0.0,
            smoothing=contour_data["smoothing"] if contour_data else 0.0,
        )
    date = (
        None
        if MapType[MapAttribute(attribute).name].value == "MIGRATION_TIME"
        else date
    )
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
    if MapType[MapAttribute(attribute).name].value == "MIGRATION_TIME":
        unit = " [year]"
    elif MapType[MapAttribute(attribute).name].value == "PLUME":
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


def _find_legend_title(attribute: MapAttribute, unit: str) -> str:
    if MapType[MapAttribute(attribute).name].value == "MIGRATION_TIME":
        return "years"
    if MapType[MapAttribute(attribute).name].value == "MASS":
        return unit
    return ""


def create_map_annotations(
    formation: str,
    surface_data: Optional[SurfaceData],
    colortables: List[Dict[str, Any]],
    attribute: MapAttribute,
    unit: str,
) -> List[wsc.ViewAnnotation]:
    annotations = []
    if (
        surface_data is not None
        and surface_data.color_map_range[0] is not None
        and surface_data.color_map_range[1] is not None
    ):
        max_value = surface_data.color_map_range[1]
        num_digits = 4 if max_value < 1 else np.ceil(np.log(max_value) / np.log(10))
        numbersize = max((6, min((17 - num_digits, 11))))
        annotations.append(
            wsc.ViewAnnotation(
                id="1_view",
                children=[
                    wsc.WebVizColorLegend(
                        title=_find_legend_title(attribute, unit),
                        min=surface_data.color_map_range[0],
                        max=surface_data.color_map_range[1],
                        colorName=surface_data.color_map_name,
                        cssLegendStyles={"top": "0", "right": "0"},
                        openColorSelector=False,
                        legendScaleSize=0.1,
                        legendFontSize=20,
                        tickFontSize=numbersize,
                        numberOfTicks=2,
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
    realizations: List[int],
    formation: str,
    surface_data: Optional[SurfaceData],
    fault_polygon_url: Optional[str],
    containment_bounds_url: Optional[str],
    haz_bounds_url: Optional[str],
    well_pick_provider: Optional[EnsembleWellPicks],
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
        containment_bounds_url is not None
        and LayoutLabels.SHOW_CONTAINMENT_POLYGON in options_dialog_options
    ):
        layers.append(
            {
                "@@type": "GeoJsonLayer",
                "name": "Containment Polygon",
                "id": "license-boundary-layer",
                "data": containment_bounds_url,
                "stroked": False,
                "getFillColor": [0, 172, 0, 120],
                "visible": True,
            }
        )

    if (
        haz_bounds_url is not None
        and LayoutLabels.SHOW_HAZARDOUS_POLYGON in options_dialog_options
    ):
        layers.append(
            {
                "@@type": "GeoJsonLayer",
                "name": "Hazardous Polygon",
                "id": "hazardous-boundary-layer",
                "data": haz_bounds_url,
                "stroked": False,
                "getFillColor": [200, 0, 0, 120],
                "visible": True,
            }
        )

    if (
        well_pick_provider is not None
        and formation is not None
        and len(realizations) > 0
        and LayoutLabels.SHOW_WELLS in options_dialog_options
    ):
        layer = well_pick_provider.geojson_layer(
            realizations[0], selected_wells, formation
        )
        if layer is not None:
            layers.append(layer)

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
    table_provider: ContainmentDataProvider,
    co2_scale: Union[Co2MassScale, Co2VolumeScale],
    realizations: List[int],
    y_limits: List[Optional[float]],
    containment_info: ContainmentInfo,
    legenddata: LegendData,
) -> Tuple[go.Figure, go.Figure, go.Figure]:
    try:
        fig0 = generate_co2_volume_figure(
            table_provider,
            table_provider.realizations,
            co2_scale,
            containment_info,
            legenddata["bar_legendonly"],
        )
        fig1 = (
            generate_co2_time_containment_figure(
                table_provider,
                realizations,
                co2_scale,
                containment_info,
                legenddata["time_legendonly"],
            )
            if len(realizations) > 1
            else generate_co2_time_containment_one_realization_figure(
                table_provider,
                co2_scale,
                realizations[0],
                y_limits,
                containment_info,
            )
        )
        if (
            containment_info.statistics_tab_option
            == StatisticsTabOption.PROBABILITY_PLOT
        ):
            fig2 = generate_co2_statistics_figure(
                table_provider,
                realizations,
                co2_scale,
                containment_info,
                legenddata["stats_legendonly"],
            )
        else:  # "box_plot"
            # Deliberately uses same legend as statistics
            fig2 = generate_co2_box_plot_figure(
                table_provider,
                realizations,
                co2_scale,
                containment_info,
                legenddata["stats_legendonly"],
            )
    except KeyError as exc:
        warnings.warn(f"Could not generate CO2 figures: {exc}")
        raise exc
    return fig0, fig1, fig2


def generate_unsmry_figures(
    table_provider_unsmry: UnsmryDataProvider,
    co2_mass_scale: Union[Co2MassScale, Co2VolumeScale],
    table_provider_containment: ContainmentDataProvider,
) -> go.Figure:
    return generate_summary_figure(
        table_provider_unsmry,
        co2_mass_scale,
        table_provider_containment,
    )


def process_visualization_info(
    attribute: str,
    thresholds: dict,
    unit: str,
    stored_info: Dict[str, Any],
    cache: Cache,
) -> Dict[str, Any]:
    """
    Clear surface cache if the threshold for visualization or mass unit is changed
    """
    stored_info["attribute"] = attribute
    stored_info["change"] = False
    if (
        MapType[MapAttribute(attribute).name].value not in ["PLUME", "MIGRATION_TIME"]
        and unit != stored_info["unit"]
    ):
        stored_info["unit"] = unit
        stored_info["change"] = True
    if thresholds is not None:
        for att in stored_info["thresholds"].keys():
            if stored_info["thresholds"][att] != thresholds[att]:
                stored_info["change"] = True
                stored_info["thresholds"][att] = thresholds[att]
    if stored_info["change"]:
        cache.clear()
    return stored_info


# pylint: disable=too-many-locals
def process_containment_info(
    zone: Optional[str],
    region: Optional[str],
    phase: str,
    containment: str,
    plume_group: str,
    color_choice: str,
    mark_choice: Optional[str],
    sorting: str,
    lines_to_show: str,
    date_option: str,
    statistics_tab_option: StatisticsTabOption,
    box_show_points: str,
    menu_options: MenuOptions,
) -> ContainmentInfo:
    if mark_choice is None:
        mark_choice = "phase"
    zones = menu_options["zones"]
    regions = menu_options["regions"]
    plume_groups = menu_options["plume_groups"]
    if len(zones) > 0:
        zones = [zone_name for zone_name in zones if zone_name != "all"]
    if len(regions) > 0:
        regions = [reg_name for reg_name in regions if reg_name != "all"]
    if len(plume_groups) > 0:
        plume_groups = [pg_name for pg_name in plume_groups if pg_name != "all"]

        def plume_sort_key(name: str) -> int:
            if name == "undetermined":
                return 999
            return name.count("+")

        plume_groups = sorted(plume_groups, key=plume_sort_key)

    if "zone" in [mark_choice, color_choice]:
        region = "all"
    if "region" in [mark_choice, color_choice]:
        zone = "all"
    return ContainmentInfo(
        zone=zone,
        region=region,
        zones=zones,
        regions=regions,
        phase=phase,
        containment=containment,
        plume_group=plume_group,
        color_choice=color_choice,
        mark_choice=mark_choice,
        sorting=sorting,
        phases=[phase for phase in menu_options["phases"] if phase != "total"],
        containments=["hazardous", "outside", "contained"],
        plume_groups=plume_groups,
        use_stats=lines_to_show == "stat",
        date_option=date_option,
        statistics_tab_option=statistics_tab_option,
        box_show_points=box_show_points,
    )


def make_plot_ids(
    ensemble: str,
    source: GraphSource,
    scale: Union[Co2MassScale, Co2VolumeScale],
    containment_info: ContainmentInfo,
    realizations: List[int],
    # lines_to_show: str,
    num_figs: int,
) -> List[str]:
    """
    Removed some keywords from plot id that we don't want to trigger updates for
    with respect to visible legends and potentially zoom level.

    Note: Currently the legends are reset if you swap to a plot with different plot id
    and back, so it works temporarily, in a sense. This might be good enough for now.
    If we want to store it more extensively, we need to do something like what's been
    outlined in _plugin.py.
    """
    zone_str = containment_info.zone if containment_info.zone is not None else "None"
    region_str = (
        containment_info.region if containment_info.region is not None else "None"
    )
    plume_group_str = (
        containment_info.plume_group
        if containment_info.plume_group is not None
        else "None"
    )
    mark_choice_str = (
        containment_info.mark_choice
        if containment_info.mark_choice is not None
        else "None"
    )
    plot_id = "-".join(
        (
            ensemble,
            source,
            scale,
            zone_str,
            region_str,
            plume_group_str,
            str(containment_info.phase),
            str(containment_info.containment),
            containment_info.color_choice,
            mark_choice_str,
            containment_info.sorting,
            containment_info.date_option,
        )
    )
    ids = [plot_id] * num_figs
    # ids += [plot_id + f"-{realizations}"] * (num_figs - 1)
    # ids[1] += f"-{lines_to_show}"
    ids[1] += "-single" if len(realizations) == 1 else "-multiple"
    ids[2] += f"-{containment_info.statistics_tab_option}"
    return ids


def set_plot_ids(
    figs: List[go.Figure],
    plot_ids: List[str],
) -> None:
    for fig, plot_id in zip(figs, plot_ids):
        if fig != no_update:
            fig["layout"]["uirevision"] = plot_id


def process_summed_mass(
    formation: str,
    realization: List[int],
    datestr: str,
    attribute: MapAttribute,
    summed_mass: Optional[float],
    surf_data: Optional[SurfaceData],
    summed_co2: Dict[str, float],
    unit: str,
) -> Tuple[Optional[SurfaceData], Dict[str, float]]:
    summed_co2_key = f"{formation}-{realization[0]}-{datestr}-{attribute}-{unit}"
    if len(realization) == 1:
        if MapType[MapAttribute(attribute).name].value == "MASS":
            if summed_mass is not None and summed_co2_key not in summed_co2:
                summed_co2[summed_co2_key] = summed_mass
            if summed_co2_key in summed_co2 and surf_data is not None:
                surf_data.readable_name += (
                    f" ({unit}) (Total: {summed_co2[summed_co2_key]:.2E}): "
                )
    return surf_data, summed_co2
