import xtgeo
from webviz_config.common_cache import CACHE


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def load_well(well_path):
    return xtgeo.Well(well_path)


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
                "color": "red",
                "positions": positions,
                "tooltip": name,
            }
        ],
    }
