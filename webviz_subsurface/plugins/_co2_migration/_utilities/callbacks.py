import logging
import warnings
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import geojson
import numpy as np
import plotly.graph_objects as go
import webviz_subsurface_components as wsc
from dash import dcc, html

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
from webviz_subsurface.plugins._co2_migration._types import LegendData
from webviz_subsurface.plugins._co2_migration._utilities.co2volume import (
    complete_missing_spatial_data,
    extract_df_from_fig,
    generate_co2_box_plot_figure,
    generate_co2_probability_figure,
    generate_co2_time_containment_figure,
    generate_co2_time_containment_one_realization_figure,
    generate_co2_volume_figure,
)
from webviz_subsurface.plugins._co2_migration._utilities.containment_data_provider import (
    ContainmentDataProvider,
)
from webviz_subsurface.plugins._co2_migration._utilities.containment_info import (
    ContainmentInfo,
    MainTabOption,
)
from webviz_subsurface.plugins._co2_migration._utilities.ensemble_well_picks import (
    EnsembleWellPicks,
)
from webviz_subsurface.plugins._co2_migration._utilities.generic import (
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
from webviz_subsurface.plugins._co2_migration._utilities.summary_graphs import (
    generate_summary_figure,
)
from webviz_subsurface.plugins._co2_migration._utilities.surface_publishing import (
    SurfaceTransform,
    TruncatedSurfaceAddress,
    publish_and_get_surface_metadata,
)
from webviz_subsurface.plugins._co2_migration._utilities.unsmry_data_provider import (
    UnsmryDataProvider,
)

LOGGER = logging.getLogger(__name__)


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
        transform: SurfaceTransform,
    ) -> Tuple[Any, Optional[Any]]:
        surf_meta, img_url, summed_mass = publish_and_get_surface_metadata(
            server,
            provider,
            address,
            transform,
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
    plume_data: Optional[Dict[str, Any]],
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
            threshold=plume_data["threshold"] if plume_data else 0.0,
            smoothing=plume_data["smoothing"] if plume_data else 0.0,
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


def _find_legend_title(attribute: MapAttribute, unit: str) -> str:
    if MapType[MapAttribute(attribute).name].value == "MIGRATION_TIME":
        return "years"
    if MapType[MapAttribute(attribute).name].value == "MASS":
        return unit
    return ""


def _create_summed_mass_annotation(
    attribute: MapAttribute,
    summed_mass: Optional[float],
    unit: str,
) -> html.Div:
    annotation: Union[html.P, str] = (
        html.P(
            [
                f"Total {MapAttribute[attribute.name].value.lower()}:",
                html.Br(),
                f"{summed_mass:.2f} {unit}",
            ]
        )
        if MapType[attribute.name].value == "MASS" and summed_mass is not None
        else ""
    )
    return html.Div(
        annotation,
        style={
            "position": "absolute",
            "top": "210px",
            "right": "4px",
            "backgroundColor": "rgba(255,255,255,0.8)",
            "padding": "1px 1px",
            "fontWeight": "bold",
            "fontSize": "15px",
            "display": "block",
        },
    )


def _create_polygon_legend(
    options: List[str],
    con_url: Optional[str],
    haz_url: Optional[str],  # Keep for backward compatibility
    nogo_url: Optional[str],
) -> List:
    legend: List = []
    hide_con = con_url is None or LayoutLabels.SHOW_CONTAINMENT_POLYGON not in options
    hide_nogo = (
        nogo_url is None and haz_url is None
    ) or LayoutLabels.SHOW_NOGO_POLYGON not in options
    outline = LayoutLabels.SHOW_POLYGONS_AS_OUTLINES in options
    if hide_con and hide_nogo:
        return legend
    legend_items = []
    square = {"width": "12px", "height": "12px", "marginRight": "6px"}
    text = {"color": "black", "fontSize": "14px"}
    if not hide_con:
        legend_items.append(
            html.Div(
                style={"display": "flex", "alignItems": "center"},
                children=[
                    html.Div(
                        style={
                            **square,
                            "backgroundColor": (
                                "transparent" if outline else "rgba(0, 172, 0, 0.47)"
                            ),
                            "border": (
                                "3px solid rgba(0, 172, 0, 0.70)"
                                if outline
                                else "transparent"
                            ),
                        }
                    ),
                    html.Div("Containment Polygon", style=text),
                ],
            )
        )
    if not hide_nogo:
        legend_items.append(
            html.Div(
                style={"display": "flex", "alignItems": "center"},
                children=[
                    html.Div(
                        style={
                            **square,
                            "backgroundColor": (
                                "transparent" if outline else "rgba(200, 0, 0, 0.47)"
                            ),
                            "border": (
                                "3px solid rgba(200, 0, 0, 0.70)"
                                if outline
                                else "transparent"
                            ),
                        }
                    ),
                    html.Div("No-go Polygon", style=text),
                ],
            )
        )
    legend.append(
        html.Div(
            children=legend_items,
            style={
                "position": "absolute",
                "top": "50px",
                "left": "4px",
                "backgroundColor": "rgba(255,255,255,0.9)",
                "padding": "6px 8px",
                "borderRadius": "4px",
                "boxShadow": "0 0 4px rgba(0,0,0,0.2)",
                "zIndex": 10,
            },
        )
    )
    return legend


# pylint: disable=too-many-arguments, too-many-locals
def create_map_annotations(
    formation: str,
    surface_data: Optional[SurfaceData],
    colortables: List[Dict[str, Any]],
    attribute: MapAttribute,
    unit: str,
    current_total: Optional[float],
    options: List[str],
    con_url: Optional[str],
    haz_url: Optional[str],
    nogo_url: Optional[str],
) -> List[Any]:
    annotations = []
    if (
        surface_data is not None
        and surface_data.color_map_range[0] is not None
        and surface_data.color_map_range[1] is not None
    ):
        max_value = surface_data.color_map_range[1]
        num_digits = 4 if max_value < 1 else np.ceil(np.log(max_value) / np.log(10))
        numbersize = max((6, min((17 - num_digits, 11))))
        annotations = [
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
            _create_summed_mass_annotation(attribute, current_total, unit),
        ] + _create_polygon_legend(options, con_url, haz_url, nogo_url)
    return annotations


# pylint: disable=too-many-arguments
def create_map_layers(
    realizations: List[int],
    formation: str,
    surface_data: Optional[SurfaceData],
    fault_polygon_url: Optional[str],
    containment_bounds_url: Optional[str],
    nogo_bounds_url: Optional[str],
    hazardous_bounds_url: Optional[str],  # Keep for backward compatibility
    well_pick_provider: Optional[EnsembleWellPicks],
    overlay_dialog_options: List[str],
    selected_wells: List[str],
    show_contours: bool,
    num_contours: Optional[float],
) -> List[Dict]:
    layers = []
    outline = LayoutLabels.SHOW_POLYGONS_AS_OUTLINES in overlay_dialog_options
    if surface_data is not None:
        # Update ColormapLayer
        meta = surface_data.meta_data

        # Generate contour lines
        contours: Dict[str, Any] = {"contours": False}
        if (
            show_contours
            and surface_data.color_map_range[0] is not None
            and surface_data.color_map_range[1] is not None
            and num_contours is not None
        ):
            min_val, max_val = surface_data.color_map_range
            assert min_val is not None and max_val is not None
            buffer = 0.01 * (max_val - min_val)  # Strange effects at min_val/max_val
            step = (max_val - min_val + 2 * buffer) / (np.round(num_contours) + 1)
            contours = {
                "contours": True,
                "contourReferencePoint": min_val + step - buffer,
                "contourInterval": step,
            }

        layers.append(
            {
                "@@type": "ColormapLayer",
                "id": "colormap-layer",
                "name": surface_data.readable_name,
                "image": surface_data.img_url,
                "bounds": meta.deckgl_bounds,
                "rotDeg": meta.deckgl_rot_deg,
                "valueRange": surface_data.value_range,
                "colorMapName": surface_data.color_map_name,
                "colorMapRange": surface_data.color_map_range,
                **contours,
            }
        )

    if (
        fault_polygon_url is not None
        and LayoutLabels.SHOW_FAULTPOLYGONS in overlay_dialog_options
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
        and LayoutLabels.SHOW_CONTAINMENT_POLYGON in overlay_dialog_options
    ):
        layers.append(
            {
                "@@type": "GeoJsonLayer",
                "name": "Containment Polygon",
                "id": "license-boundary-layer",
                "data": containment_bounds_url,
                "stroked": outline,
                "filled": not outline,
                "getFillColor": [0, 172, 0, 120],
                "getLineColor": [0, 172, 0, 120],
                "getLineWidth": 3,
                "lineWidthUnits": "pixels",
                "visible": True,
            }
        )

    if (
        nogo_bounds_url is not None
        and LayoutLabels.SHOW_NOGO_POLYGON in overlay_dialog_options
    ):
        layers.append(
            {
                "@@type": "GeoJsonLayer",
                "name": "No-go Polygon",
                "id": "nogo-boundary-layer",
                "data": nogo_bounds_url,
                "stroked": outline,
                "filled": not outline,
                "getFillColor": [200, 0, 0, 120],
                "getLineColor": [200, 0, 0, 180],
                "getLineWidth": 3,
                "lineWidthUnits": "pixels",
                "visible": True,
            }
        )

    if (
        hazardous_bounds_url is not None
        and LayoutLabels.SHOW_NOGO_POLYGON in overlay_dialog_options
    ):
        layers.append(
            {
                "@@type": "GeoJsonLayer",
                "name": "No-go Polygon",
                "id": "hazardous-boundary-layer",
                "data": hazardous_bounds_url,
                "stroked": outline,
                "filled": not outline,
                "getFillColor": [200, 0, 0, 120],
                "getLineColor": [200, 0, 0, 180],
                "getLineWidth": 3,
                "lineWidthUnits": "pixels",
                "visible": True,
            }
        )

    if (
        well_pick_provider is not None
        and formation is not None
        and len(realizations) > 0
        and LayoutLabels.SHOW_WELLS in overlay_dialog_options
    ):
        layer = well_pick_provider.geojson_layer(
            realizations[0], selected_wells, formation
        )
        if layer is not None:
            layers.append(layer)
    return layers


def generate_containment_figure(
    table_provider: ContainmentDataProvider,
    active_tab: MainTabOption,
    co2_scale: Union[Co2MassScale, Co2VolumeScale],
    realizations: List[int],
    y_limits: List[Optional[float]],
    containment_info: ContainmentInfo,
    legenddata: LegendData,
) -> go.Figure:
    try:
        containment_df = table_provider.extract_dataframes(realizations)
        containment_df = complete_missing_spatial_data(
            containment_df, containment_info, active_tab
        )
        if active_tab == MainTabOption.CONTAINMENT_STATE:
            return generate_co2_volume_figure(
                containment_df,
                co2_scale,
                containment_info,
                legenddata["bar_legendonly"],
            )
        if active_tab == MainTabOption.CONTAINMENT_OVER_TIME:
            if len(realizations) > 1:
                return generate_co2_time_containment_figure(
                    containment_df,
                    co2_scale,
                    containment_info,
                    legenddata["time_legendonly"],
                )
            return generate_co2_time_containment_one_realization_figure(
                containment_df,
                co2_scale,
                y_limits,
                containment_info,
            )
        if active_tab == MainTabOption.PROBABILITY:
            return generate_co2_probability_figure(
                containment_df,
                co2_scale,
                containment_info,
                legenddata["probability_legendonly"],
            )
        if active_tab == MainTabOption.BOX_PLOT:
            return generate_co2_box_plot_figure(
                containment_df,
                co2_scale,
                containment_info,
                legenddata["box_legendonly"],
            )
        raise ValueError(f"Unsupported containment tab: {active_tab}")
    except Exception as exc:
        warnings.warn(f"Could not generate CO2 figure: {exc}")
        raise Exception(f"{exc}")


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


def find_table_date(
    slider_dates: List[str], date_index: Optional[int], table_dates: List[str]
) -> Optional[str]:
    if date_index is None:
        return None
    # Map dates are formatted YYYYMMDD, table dates YYYY-MM-DD
    date = slider_dates[date_index].replace("-", "")
    return next((d for d in table_dates if d.replace("-", "") == date), None)


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
    show_realizations: bool,
    date_option: str,
    show_all_points: bool,
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
        containments=["nogo", "outside", "contained"],
        plume_groups=plume_groups,
        show_realizations=show_realizations,
        date_option=date_option,
        points_to_show="all" if show_all_points else "outliers",
    )


def make_plot_generation_key(
    active_tab: MainTabOption,
    ensemble: str,
    source: GraphSource,
    co2_scale: Union[Co2MassScale, Co2VolumeScale],
    realizations: List[int],
    y_limits: List[Optional[float]],
    containment_info: Optional[ContainmentInfo],
) -> Dict[str, Any]:
    key: Dict[str, Any] = {}

    if not realizations:
        key["empty"] = "no-realizations"
        return key

    if source == GraphSource.UNSMRY:
        key["source"] = source.value
        if active_tab == MainTabOption.CONTAINMENT_OVER_TIME:
            key.update(ensemble=ensemble, scale=co2_scale.value)
        return key

    if containment_info is None:
        raise ValueError("Containment information is required for containment plots")

    split_dimensions = {
        containment_info.color_choice,
        containment_info.mark_choice,
    }
    key.update(
        ensemble=ensemble,
        source=source.value,
        scale=co2_scale.value,
        realizations=list(realizations),
        color_choice=containment_info.color_choice,
        mark_choice=containment_info.mark_choice,
        sorting=(
            containment_info.sorting if containment_info.mark_choice != "none" else None
        ),
        filters={
            dimension: getattr(containment_info, dimension)
            for dimension in (
                "zone",
                "region",
                "phase",
                "containment",
                "plume_group",
            )
            if dimension not in split_dimensions
        },
    )

    if active_tab == MainTabOption.CONTAINMENT_STATE:
        key["date_option"] = containment_info.date_option
    elif active_tab == MainTabOption.CONTAINMENT_OVER_TIME:
        if len(realizations) == 1:
            key.update(time_mode="single", y_limits=list(y_limits))
        else:
            key["time_mode"] = (
                "realizations" if containment_info.show_realizations else "statistics"
            )
    elif active_tab == MainTabOption.PROBABILITY:
        key["date_option"] = containment_info.date_option
    elif active_tab == MainTabOption.BOX_PLOT:
        key.update(
            date_option=containment_info.date_option,
            points_to_show=containment_info.points_to_show,
        )

    return key


def make_plot_id(
    ensemble: str,
    source: GraphSource,
    scale: Union[Co2MassScale, Co2VolumeScale],
    containment_info: ContainmentInfo,
    realizations: List[int],
    active_tab: MainTabOption,
) -> str:
    """
    Make plot id for maintaining visible legends and zoom level.
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
            source.value,
            scale.value,
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
    if active_tab == MainTabOption.CONTAINMENT_OVER_TIME:
        plot_id += "-single" if len(realizations) == 1 else "-multiple"
    return plot_id


def process_summed_mass(
    formation: str,
    realization: List[int],
    datestr: Optional[str],
    attribute: MapAttribute,
    summed_mass: Optional[float],
    summed_co2: Dict[str, float],
    unit: str,
) -> Tuple[Optional[float], Dict[str, float]]:
    summed_co2_key = f"{formation}-{realization[0]}-{datestr}-{attribute}-{unit}"
    current_total = None
    if len(realization) == 1:
        if MapType[MapAttribute(attribute).name].value == "MASS":
            if summed_mass is not None and summed_co2_key not in summed_co2:
                summed_co2[summed_co2_key] = summed_mass
            if summed_co2_key in summed_co2:
                current_total = summed_co2[summed_co2_key]
    return current_total, summed_co2


def export_figure_data_to_csv(
    figure: Dict, file_name: str, plot_choice: str
) -> Optional[Dict[str, Any]]:
    """Export visible figure data to CSV file"""
    try:
        figure_go = go.Figure(figure)  # Dash State returns dict
        df = extract_df_from_fig(figure_go.data, plot_choice)
        if df.empty:
            LOGGER.warning("No plot data to export to CSV file.")
            return None

        result = dcc.send_data_frame(df.to_csv, filename=file_name, index=False)
        return result

    except (ValueError, KeyError, AttributeError, TypeError) as e:
        LOGGER.warning(f"Failed to export plot data to CSV file: {e}")
        return None
