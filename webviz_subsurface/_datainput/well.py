import xtgeo
import numpy as np

from webviz_config.common_cache import CACHE


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def load_well(well_path):
    return xtgeo.Well(well_path)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def make_well_layer(well, name="well", zmin=0):
    """Make LayeredMap well polyline"""
    well.dataframe = well.dataframe[well.dataframe["Z_TVDSS"] > zmin]
    positions = well.dataframe[["X_UTME", "Y_UTMN"]].values
    return {
        "name": name,
        "checked": True,
        "base_layer": False,
        "data": [
            {
                "type": "polyline",
                "color": "black",
                "positions": positions,
                "tooltip": name,
            }
        ],
    }


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def make_well_layers(wellfiles, zmin=0, max_points=100):
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
    wells,
    planned_wells,
    surface_name,
    surface,
    dropdown_file,
):
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
    data = []
    planned_data = []
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


def append_well_to_data(data, well, wellfile, surface, color):
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
