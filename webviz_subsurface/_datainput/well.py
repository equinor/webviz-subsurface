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
                "color": "red",
                "positions": positions,
                "tooltip": name,
            }
        ],
    }


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def make_well_layers(fns, zmin=0):
    """Make layeredmap wells layer"""
    data = []
    for fn in fns:
        well = load_well(fn)
        well.dataframe = well.dataframe[well.dataframe["Z_TVDSS"] > zmin]
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
