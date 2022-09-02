import pathlib
from enum import Enum
from typing import Dict, Iterable, Optional

import numpy as np
from fmu.ensemble import ScratchEnsemble


def fmu_realization_paths(ensemble_path) -> Dict[int, str]:
    scratch = ScratchEnsemble("tmp", paths=ensemble_path)
    return {
        r: s.runpath()
        for r, s in scratch.realizations.items()
    }


def first_existing_fmu_file_path(
    ens_root: str,
    realizations: Iterable[int],
    relpath: str,
) -> Optional[str]:
    rp = fmu_realization_paths(ens_root)
    for r in realizations:
        fn = pathlib.Path(rp[r]) / relpath
        if fn.is_file():
            return str(fn)
    return None


class MapAttribute(Enum):
    MIGRATION_TIME = "Migration Time"
    MAX_SGAS = "Maximum SGAS"
    MAX_AMFG = "Maximum AMFG"
    SGAS_PLUME = "Plume (SGAS)"
    AMFG_PLUME = "Plume (AMFG)"


def parse_polygon_file(filename: str):
    xyz = np.genfromtxt(filename, skip_header=1, delimiter=",")
    as_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "LineString",
                    "coordinates": xyz[:, :2].tolist(),
                }
            }
        ]
    }
    return as_geojson
