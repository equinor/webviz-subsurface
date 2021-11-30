from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import xtgeo
from webviz_config.common_cache import CACHE


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def load_well(
    wfile: Union[str, Path],
    zonelogname: Optional[str] = None,
    mdlogname: Optional[str] = None,
    lognames: Optional[List[str]] = None,
) -> xtgeo.Well:
    lognames = [] if not lognames else lognames
    if zonelogname is not None and zonelogname not in lognames:
        lognames.append(zonelogname)
    if mdlogname is not None and mdlogname not in lognames:
        lognames.append(mdlogname)
    well = xtgeo.well_from_file(
        wfile=wfile, zonelogname=zonelogname, mdlogname=mdlogname, lognames=lognames
    )

    # Create a relative XYLENGTH vector (0.0 where well starts)
    well.create_relative_hlen()
    return well


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def make_well_layer(
    well: xtgeo.Well, name: str = "well", zmin: float = 0
) -> Dict[str, Any]:
    """Make LayeredMap well polyline"""
    well.dataframe = well.dataframe[well.dataframe["Z_TVDSS"] > zmin]
    positions = well.dataframe[["X_UTME", "Y_UTMN"]].values
    return {
        "name": "Well",
        "id": "Well",
        "checked": True,
        "baseLayer": False,
        "action": "update",
        "data": [
            {
                "type": "polyline",
                "color": "black",
                "positions": positions,
                "id": name,
                "tooltip": name,
            },
            {
                "type": "circle",
                "center": positions[0],
                "radius": 60,
                "color": "black",
                "tooltip": "A",
            },
            {
                "type": "circle",
                "center": positions[-1],
                "radius": 60,
                "color": "black",
                "tooltip": "A'",
            },
        ],
    }


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def make_well_layers(
    wellfiles: List[str], zmin: float = 0, max_points: float = 100
) -> Dict[str, Any]:
    """Make layeredmap wells layer"""
    data = []
    for wellfile in wellfiles:
        try:
            well = load_well(wellfile)
        except ValueError:
            continue
        well.dataframe = well.dataframe[well.dataframe["Z_TVDSS"] > zmin]
        while len(well.dataframe.values) > max_points:
            well.downsample()
        positions = well.dataframe[["X_UTME", "Y_UTMN"]].values
        data.append(
            {
                "type": "polyline",
                "color": "black",
                "positions": positions,
                "tooltip": well.name,
            }
        )
    return {"name": "Wells", "checked": True, "base_layer": False, "data": data}


def get_well_layers(
    wells: Dict[str, xtgeo.Well],
    planned_wells: Dict[str, xtgeo.Well],
    surface_name: str,
    surface: xtgeo.RegularSurface,
    dropdown_file: str,
) -> List[Dict[str, Any]]:
    """Make circles around well in layered map view
    Args:
        wells: dictionary of  type {wellfile: xtgeo.Well(wellfile)}
        planned_wells: dictionary of type {wellfile: xtgeo.Well(wellfile)}
        surface_name: Name of surface
        surface: xtgeo surface
        dropdown_file: A well file from dropdown value
    Returns:
        List of well layers with data for well circles and trajectory
    """
    data: List[Dict[str, Any]] = []
    planned_data: List[Dict[str, Any]] = []
    dropdown_well = (
        wells[dropdown_file] if dropdown_file in wells else planned_wells[dropdown_file]
    )
    dropdown_well_df = dropdown_well.dataframe[dropdown_well.dataframe["Z_TVDSS"] > 0]
    positions = dropdown_well_df[["X_UTME", "Y_UTMN"]].values
    dropdown_data = [
        {
            "type": "polyline",
            "color": "rgba(128,0,0)",
            "positions": positions,
            "tooltip": dropdown_well.wellname + " trajectory",
        }
    ]
    for wellfile, well in wells.items():
        color = "rgba(128,0,0)" if wellfile == dropdown_file else "rgba(255,20,147)"
        append_well_to_data(data, well, wellfile, surface, color)
    for wellfile, well in planned_wells.items():
        color = "rgba(128,0,0)" if wellfile == dropdown_file else "rgba(224,224,224,1)"
        append_well_to_data(planned_data, well, wellfile, surface, color)
    return [
        {
            "name": "Wells",
            "checked": True,
            "baseLayer": False,
            "data": data,
            "id": surface_name + "-wells",
            "action": "add",
        },
        {
            "name": "Planned wells",
            "checked": True,
            "baselayer": False,
            "data": planned_data,
            "id": surface_name + "-planned-wells",
            "action": "add",
        },
        {
            "name": dropdown_well.wellname + "-trajectory",
            "checked": True,
            "baseLayer": False,
            "data": dropdown_data,
            "action": "add",
            "id": surface_name + "-well-trajectory",
        },
    ]


def append_well_to_data(
    data: List[Dict[str, Any]],
    well: xtgeo.Well,
    wellfile: str,
    surface: str,
    color: str,
) -> None:
    with np.errstate(invalid="ignore"):
        surface_picks = well.get_surface_picks(surface)
        # get_surface_picks raises warning when MD column is missing in well
    if surface_picks is not None:
        surface_picks_df = surface_picks.dataframe
        coordinates = surface_picks_df[["X_UTME", "Y_UTMN"]].values
        for coord in coordinates:
            data.append(
                {
                    "type": "circle",
                    "center": coord,
                    "color": color,
                    "radius": 100,
                    "tooltip": well.wellname,
                    "id": wellfile,
                }
            )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def create_leaflet_well_marker_layer(
    wells: List[xtgeo.Well],
    surface: xtgeo.RegularSurface,
    color: str = "red",
    size: int = 100,
) -> Dict:
    data = []
    for well in wells:

        with np.errstate(invalid="ignore"):
            surface_picks = well.get_surface_picks(surface)
        if surface_picks is None:
            continue
        surface_picks_df = surface_picks.dataframe
        coordinates = surface_picks_df[["X_UTME", "Y_UTMN", "Z_TVDSS"]].values
        for coord in coordinates:
            data.append(
                {
                    "type": "circle",
                    "center": [coord[0], coord[1]],
                    "color": color,
                    "radius": size,
                    "tooltip": f"<b>{well.name} <br> TVDSS:</b> {round(coord[2],2)}",
                    "id": well.name,
                }
            )
    return {
        "id": "WellTops",
        "name": "WellTops",
        "baseLayer": False,
        "checked": True,
        "action": "update",
        "data": data,
    }
