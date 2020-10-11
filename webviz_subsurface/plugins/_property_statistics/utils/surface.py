import pathlib

import xtgeo
from webviz_config.webviz_store import webvizstore


def surface_from_zone_prop(
    parent, zone: str, prop: str, ensemble: str, stype: str
) -> dict:

    path = get_surface_path(
        ens_path=parent.surface_folders[ensemble],
        statistic=stype,
        zone=zone,
        prop=prop,
    )
    try:
        return xtgeo.surface_from_file(path.resolve())
    except OSError:
        surf = xtgeo.RegularSurface()
        surf.values = 0
        return surf


def surface_store(parent) -> list:
    """Function to copy all relevant statistical surfaces
    to store"""
    zones = parent.pmodel.dataframe["ZONE"].unique()
    properties = parent.pmodel.dataframe["PROPERTY"].unique()
    ensembles = parent.pmodel.ensembles
    statistics = ["mean", "stddev", "min", "max", "p10", "p90"]
    store_funcs = []
    for ensemble in ensembles:
        for zone in zones:
            for prop in properties:
                for statistic in statistics:
                    store_funcs.append(
                        (
                            get_surface_path,
                            [
                                {
                                    "ens_path": parent.surface_folders[ensemble],
                                    "statistic": statistic,
                                    "zone": parent.surface_renaming.get(zone, zone),
                                    "prop": parent.surface_renaming.get(prop, prop),
                                }
                            ],
                        )
                    )
    return store_funcs


@webvizstore
def get_surface_path(ens_path, statistic, zone, prop) -> pathlib.Path:
    return ens_path / statistic / f"{zone}--{prop}.gri"
