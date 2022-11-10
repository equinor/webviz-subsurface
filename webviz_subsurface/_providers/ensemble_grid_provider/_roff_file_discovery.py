import glob
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from fmu.ensemble import ScratchEnsemble


@dataclass(frozen=True)
class GridParameterFileInfo:
    path: str
    real: int
    name: str
    attribute: str
    datestr: Optional[str]


@dataclass(frozen=True)
class GridParameterIdent:
    name: str
    attribute: str
    datestr: Optional[str]


@dataclass(frozen=True)
class GridFileInfo:
    path: str
    real: int
    name: str


@dataclass(frozen=True)
class GridIdent:
    name: str


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


def ident_from_filename(
    filename: str,
) -> Union[GridIdent, GridParameterIdent]:
    """Split the stem part of the roff filename into grid name, attribute and
    optionally date part"""
    delimiter: str = "--"
    parts = Path(filename).stem.split(delimiter)
    if len(parts) == 1:
        return GridIdent(name=parts[0])

    return GridParameterIdent(
        name=parts[0], attribute=parts[1], datestr=parts[2] if len(parts) >= 3 else None
    )


def discover_per_realization_roff_files(
    ens_path: str, grid_name: str, attribute_filter: List[str] = None
) -> Tuple[List[GridFileInfo], List[GridParameterFileInfo]]:
    rel_folder: str = "share/results/grids"
    suffix: str = "*.roff"

    grid_parameters_info: List[GridParameterFileInfo] = []
    grid_info: List[GridFileInfo] = []
    real_dict = _discover_ensemble_realizations_fmu(ens_path)
    for realnum, runpath in sorted(real_dict.items()):
        globbed_filenames = glob.glob(str(Path(runpath) / rel_folder / suffix))
        for filename in sorted(globbed_filenames):
            ident = ident_from_filename(filename)
            if ident.name != grid_name:
                continue
            if isinstance(ident, GridParameterIdent):
                if (
                    attribute_filter is not None
                    and ident.attribute not in attribute_filter
                ):
                    continue
                grid_parameters_info.append(
                    GridParameterFileInfo(
                        path=filename,
                        real=realnum,
                        name=ident.name,
                        attribute=ident.attribute,
                        datestr=ident.datestr,
                    )
                )
            else:
                grid_info.append(
                    GridFileInfo(path=filename, real=realnum, name=ident.name)
                )

    return grid_info, grid_parameters_info
