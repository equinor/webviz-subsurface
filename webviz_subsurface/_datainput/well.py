import xtgeo

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


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_well_layers(
    well_list, surface_name, surface, dropdown_well, radius=100, color="red"
):
    """ Make circles around well in layered map view
    Args:
        well_list: List of all wells
        surface_name: Name of surface object
        surface: An xtgeo surface object
        dropdown_well: An xtgeo well object from dropdown menu
    Returns:
        List of well layers with data for well circles and trajectory
     """
    dropdown_well_name = dropdown_well.wellname
    dropdown_well.dataframe = dropdown_well.dataframe[
        dropdown_well.dataframe["Z_TVDSS"] > 0
    ]
    dropdown_data = []
    dropdown_data.append(
        {
            "type": "polyline",
            "color": "yellow",
            "positions": dropdown_well.dataframe[["X_UTME", "Y_UTMN"]].values,
            "tooltip": dropdown_well_name + " trajectory",
        }
    )
    data = []
    for well in well_list:
        well_name = well.wellname
        surface_picks = well.get_surface_picks(surface)
        if surface_picks is not None:
            surface_picks_df = surface_picks.dataframe
            coordinates = surface_picks_df[["X_UTME", "Y_UTMN"]].values
            for coordinate in coordinates:
                data.append(
                    {
                        "type": "circle",
                        "center": coordinate,
                        "color": "rgb(255,255,0,1.0)"
                        if dropdown_well_name == well_name
                        else color,
                        "radius": radius,
                        "tooltip": well_name,
                    }
                )
    return [
        {
            "name": "Wells",
            "checked": True,
            "baseLayer": False,
            "data": data,
            "id": surface_name + " " + "well" + "-id",
            "action": "add",
        },
        {
            "name": dropdown_well_name + " trajectory",
            "checked": True,
            "baseLayer": False,
            "data": dropdown_data,
            "action": "add",
            "id": surface_name + " " + "well_trajectory" + "-id",
        },
    ]
