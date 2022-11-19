import glob
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

# The fmu.ensemble dependency ecl is only available for Linux,
# hence, ignore any import exception here to make
# it still possible to use the PvtPlugin on
# machines with other OSes.
#
# NOTE: Functions in this file cannot be used
#       on non-Linux OSes.
try:
    from fmu.ensemble import ScratchEnsemble
except ImportError:
    pass


@dataclass(frozen=True)
class FaultPolygonsFileInfo:
    path: str
    real: int
    name: str
    attribute: str


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


@dataclass(frozen=True)
class FaultPolygonsIdent:
    name: str
    attribute: str


def _fault_polygons_ident_from_filename(filename: str) -> Optional[FaultPolygonsIdent]:
    """Split the stem part of the fault polygons filename into fault polygons name and attribute"""
    delimiter: str = "--"
    parts = Path(filename).stem.split(delimiter)
    if len(parts) != 2:
        return None

    return FaultPolygonsIdent(name=parts[0], attribute=parts[1])


def discover_per_realization_fault_polygons_files(
    ens_path: str,
) -> List[FaultPolygonsFileInfo]:
    rel_fault_polygons_folder: str = "share/results/polygons"
    suffix: str = "*.pol"

    fault_polygons_files: List[FaultPolygonsFileInfo] = []

    real_dict = _discover_ensemble_realizations_fmu(ens_path)
    for realnum, runpath in sorted(real_dict.items()):
        globbed_filenames = glob.glob(
            str(Path(runpath) / rel_fault_polygons_folder / suffix)
        )
        for fault_polygons_filename in sorted(globbed_filenames):
            fault_polygons_ident = _fault_polygons_ident_from_filename(
                fault_polygons_filename
            )
            if fault_polygons_ident:
                fault_polygons_files.append(
                    FaultPolygonsFileInfo(
                        path=fault_polygons_filename,
                        real=realnum,
                        name=fault_polygons_ident.name,
                        attribute=fault_polygons_ident.attribute,
                    )
                )

    return fault_polygons_files
