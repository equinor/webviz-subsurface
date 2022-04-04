from typing import Dict
from enum import Enum
from fmu.ensemble import ScratchEnsemble


FAULT_POLYGON_ATTRIBUTE = "dl_extracted_faultlines"


class MapAttribute(Enum):
    MIGRATION_TIME = "migration-time"
    MAX_SATURATION = "max-saturation"


def realization_paths(ensemble_path) -> Dict[str, str]:
    scratch = ScratchEnsemble("tmp", paths=ensemble_path)
    return {
        r: s.runpath()
        for r, s in scratch.realizations.items()
    }
