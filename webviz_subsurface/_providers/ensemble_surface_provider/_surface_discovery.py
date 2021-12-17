import glob
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from fmu.ensemble import ScratchEnsemble


@dataclass(frozen=True)
class SurfaceFileInfo:
    path: str
    real: int
    name: str
    attribute: str
    datestr: Optional[str]


def _discover_ensemble_realizations(ens_path: str) -> Dict[int, str]:
    """Returns dict indexed by realization number and with runpath as value"""
    scratch_ensemble = ScratchEnsemble("dummyEnsembleName", paths=ens_path).filter("OK")
    real_dict = {i: r.runpath() for i, r in scratch_ensemble.realizations.items()}
    return real_dict


@dataclass(frozen=True)
class SurfaceIdent:
    name: str
    attribute: str
    datestr: Optional[str]


def _surface_ident_from_filename(filename: str) -> Optional[SurfaceIdent]:
    """Split the stem part of the surface filename into surface name, attribute and
    optionally date part"""
    delimiter: str = "--"
    parts = Path(filename).stem.split(delimiter)
    if len(parts) < 2:
        return None

    return SurfaceIdent(
        name=parts[0], attribute=parts[1], datestr=parts[2] if len(parts) >= 3 else None
    )


def discover_per_realization_surface_files(ens_path: str) -> List[SurfaceFileInfo]:
    rel_surface_folder: str = "share/results/maps"
    suffix: str = "*.gri"

    surface_files: List[SurfaceFileInfo] = []

    real_dict = _discover_ensemble_realizations(ens_path)
    for realnum, runpath in sorted(real_dict.items()):
        globbed_filenames = glob.glob(str(Path(runpath) / rel_surface_folder / suffix))
        for surf_filename in sorted(globbed_filenames):
            surf_ident = _surface_ident_from_filename(surf_filename)
            if surf_ident:
                surface_files.append(
                    SurfaceFileInfo(
                        path=surf_filename,
                        real=realnum,
                        name=surf_ident.name,
                        attribute=surf_ident.attribute,
                        datestr=surf_ident.datestr,
                    )
                )

    return surface_files


def discover_observed_surface_files(ens_path: str) -> List[SurfaceFileInfo]:
    observed_surface_folder: str = "share/observations/maps"
    suffix: str = "*.gri"

    surface_files: List[SurfaceFileInfo] = []

    ens_root_path = ens_path.split("realization")[0]
    globbed_filenames = glob.glob(
        str(Path(ens_root_path) / observed_surface_folder / suffix)
    )
    for surf_filename in sorted(globbed_filenames):
        surf_ident = _surface_ident_from_filename(surf_filename)
        if surf_ident:
            surface_files.append(
                SurfaceFileInfo(
                    path=surf_filename,
                    real=-1,
                    name=surf_ident.name,
                    attribute=surf_ident.attribute,
                    datestr=surf_ident.datestr,
                )
            )

    return surface_files
