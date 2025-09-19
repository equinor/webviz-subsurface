from pathlib import Path
from typing import Dict

from fmu.ensemble import ScratchEnsemble


def realization_paths(ens_path: str) -> Dict[int, Path]:
    scratch_ensemble = ScratchEnsemble("_", paths=ens_path).filter("OK")
    return {i: Path(r.runpath()) for i, r in scratch_ensemble.realizations.items()}
