from typing import Dict
from enum import Enum
from fmu.ensemble import ScratchEnsemble
import numpy as np


FAULT_POLYGON_ATTRIBUTE = "dl_extracted_faultlines"


class MapAttribute(Enum):
    MIGRATION_TIME = "Migration Time"
    MAX_SGAS = "Maximum SGAS"
    MAX_AMFG = "Maximum AMFG"
    SGAS_PLUME = "Plume (SGAS)"
    AMFG_PLUME = "Plume (AMFG)"


def realization_paths(ensemble_path) -> Dict[str, str]:
    scratch = ScratchEnsemble("tmp", paths=ensemble_path)
    return {
        r: s.runpath()
        for r, s in scratch.realizations.items()
    }


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
