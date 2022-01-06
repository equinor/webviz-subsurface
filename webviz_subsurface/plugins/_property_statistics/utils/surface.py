import pathlib
from typing import Dict, List, Optional

import pandas as pd
import xtgeo
from webviz_config.webviz_store import webvizstore


def make_undefined_surface() -> xtgeo.RegularSurface:
    surf = xtgeo.RegularSurface(
        ncol=1, nrow=1, xinc=1, yinc=1
    )  # 1's as input is required
    surf.values = 0
    return surf


def surface_from_zone_prop(
    surface_table: pd.DataFrame, zone: str, prop: str, ensemble: str, stype: str
) -> xtgeo.RegularSurface:

    df = surface_table[
        (surface_table["zone"] == zone)
        & (surface_table["prop"] == prop)
        & (surface_table["ensemble"] == ensemble)
        & (surface_table["statistic"] == stype)
    ]
    if df.empty or len(df["path"].unique()) > 1:
        return make_undefined_surface()
    path = get_path(pathlib.Path(df["path"].unique()[0]))
    return xtgeo.surface_from_file(path.resolve())


@webvizstore
def generate_surface_table(
    statistics_dframe: pd.DataFrame,
    ensembles: List,
    surface_renaming: Dict,
    surface_folders: Optional[Dict],
) -> pd.DataFrame:
    surface_folders = {} if not surface_folders else surface_folders
    zones = statistics_dframe["ZONE"].unique()
    properties = statistics_dframe["PROPERTY"].unique()
    statistics = ["mean", "stddev", "min", "max", "p10", "p90"]
    surface_table = []
    for ensemble in ensembles:
        for zone in zones:
            for prop in properties:
                for statistic in statistics:
                    zone_in_file = surface_renaming.get(zone, zone)
                    prop_in_file = surface_renaming.get(prop, prop)
                    path = (
                        surface_folders.get(ensemble, pathlib.Path())
                        / statistic
                        / f"{zone_in_file}--{prop_in_file}.gri"
                    )
                    if path.exists():
                        surface_table.append(
                            {
                                "ensemble": ensemble,
                                "zone": zone,
                                "prop": prop,
                                "statistic": statistic,
                                "path": str(path),
                            }
                        )
    return (
        pd.DataFrame(surface_table)
        if surface_table
        else pd.DataFrame(columns=["ensemble", "zone", "prop", "statistic", "path"])
    )


@webvizstore
def get_path(path: pathlib.Path) -> pathlib.Path:
    return path
