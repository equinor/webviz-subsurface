import glob
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

# The fmu.ensemble dependency resdata is only available for Linux,
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
class PolygonsFileInfo:
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
class PolygonsIdent:
    name: str
    attribute: str


def _polygons_ident_from_filename(filename: str) -> Optional[PolygonsIdent]:
    """Split the stem part of the fault polygons filename into fault polygons name and attribute"""
    delimiter: str = "--"
    parts = Path(filename).stem.split(delimiter)
    if len(parts) != 2:
        return None

    return PolygonsIdent(name=parts[0], attribute=parts[1])


def discover_per_realization_polygons_files(
    ens_path: str,
    polygons_pattern: str,
) -> List[PolygonsFileInfo]:
    polygons_files: List[PolygonsFileInfo] = []

    real_dict = _discover_ensemble_realizations_fmu(ens_path)
    for realnum, runpath in sorted(real_dict.items()):
        if Path(polygons_pattern).is_absolute():
            filenames = [polygons_pattern]
        else:
            filenames = glob.glob(str(Path(runpath) / polygons_pattern))
        for polygons_filename in sorted(filenames):
            polygons_ident = _polygons_ident_from_filename(polygons_filename)
            if polygons_ident:
                polygons_files.append(
                    PolygonsFileInfo(
                        path=polygons_filename,
                        real=realnum,
                        name=polygons_ident.name,
                        attribute=polygons_ident.attribute,
                    )
                )

    return polygons_files
