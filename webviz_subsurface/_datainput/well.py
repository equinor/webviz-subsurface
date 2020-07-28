import xtgeo
from webviz_config.common_cache import CACHE
import pandas as pd


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
def get_well_layers(wellfiles, surface_name, wellpoints_file, dropdown_wellfile, radius=100, color="red"):
    """ Make circles around well in layered map view
    Args:
        wellfiles: List of all wellfiles
        surface_name: Name of surface
        wellpoints_file: Path to wellpoints.csv for conditional points (cp)
    Returns:
        well_layers: Dictionary with data for circles
     """
    df = pd.read_csv(wellpoints_file)
    cp_df = df[df["Surface"] == surface_name]  # Get conditional points
    data = []
    dropdown_well = xtgeo.Well(dropdown_wellfile)
    dropdown_well_name = dropdown_well.wellname
    for wellfile in wellfiles:
        well = xtgeo.Well(wellfile)
        well_name = well.wellname
        well_cp_df = cp_df[cp_df["Well"] == well_name]
        coordinates = well_cp_df[['x', 'y']].values
        if len(coordinates) == 0:
            data += []
        else:
            data.append({
                "type": "circle",
                "center": coordinates[0],
                "color": "yellow" if dropdown_well_name == well_name else color,
                "fillcolor": "yellow" if dropdown_well_name == well_name else color,
                "radius": radius,
                "tooltip": well_name,
                })
    return {"name": "Wells", "checked": True, "baseLayer": False, "data": data,\
            "id": surface_name + ' ' + "well" + "-id", "action": "add"}