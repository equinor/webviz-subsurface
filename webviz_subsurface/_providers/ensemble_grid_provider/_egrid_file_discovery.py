import glob
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from fmu.ensemble import ScratchEnsemble


@dataclass(frozen=True)
class EclipseCaseFileInfo:
    realization: int
    egrid_path: str
    init_path: str
    unrst_path: str


def _discover_ensemble_realizations_fmu(ens_path: str) -> Dict[int, str]:
    """Returns dict indexed by realization number and with runpath as value"""
    scratch_ensemble = ScratchEnsemble("dummyEnsembleName", paths=ens_path).filter("OK")
    real_dict = {i: r.runpath() for i, r in scratch_ensemble.realizations.items()}
    return real_dict


def _discover_ensemble_realizations(ens_path: str) -> Dict[int, str]:
    # Much faster than FMU impl above, but is it risky?
    # Do we need to check for OK-file?
    real_dict: Dict[int, str] = {}

    realidxregexp = re.compile(r"realization-(\d+)")
    globbed_real_dirs = sorted(glob.glob(str(ens_path)))
    for real_dir in globbed_real_dirs:
        realnum: Optional[int] = None
        for path_comp in reversed(real_dir.split(os.path.sep)):
            realmatch = re.match(realidxregexp, path_comp)
            if realmatch:
                realnum = int(realmatch.group(1))
                break

        if realnum is not None:
            real_dict[realnum] = real_dir

    return real_dict


def discover_per_realization_eclipse_files(
    ens_path: str, grid_name: str
) -> List[EclipseCaseFileInfo]:
    rel_folder: str = "eclipse/model"

    real_dict = _discover_ensemble_realizations_fmu(ens_path)
    eclipse_file_infos = []
    for realnum, runpath in sorted(real_dict.items()):
        globbed_model_folder = glob.glob(str(Path(runpath) / rel_folder))

        for folder in sorted(globbed_model_folder):
            egrid_file = f"{folder}/{grid_name}.EGRID"
            init_file = f"{folder}/{grid_name}.INIT"
            unrst_file = f"{folder}/{grid_name}.UNRST"
            if (
                not os.path.exists(egrid_file)
                or not os.path.exists(init_file)
                or not os.path.exists(unrst_file)
            ):
                continue
            eclipse_file_infos.append(
                EclipseCaseFileInfo(
                    realization=realnum,
                    egrid_path=egrid_file,
                    init_path=init_file,
                    unrst_path=unrst_file,
                )
            )
    if not eclipse_file_infos:
        raise ValueError(
            f"No eclipse models found at {Path(ens_path) / rel_folder / grid_name}"
        )
    return eclipse_file_infos
