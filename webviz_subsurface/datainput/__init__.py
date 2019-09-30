"""### _Subsurface data input_
Contains data processing functions used in the containers.
Some of the scripts are dependent on FMU postprocessing scripts
that will be made open source in the near future.
"""

from ._history_match import extract_mismatch, scratch_ensemble
from ._intersect import load_surface, get_wfence, get_hfence
from ._inplace_volumes import extract_volumes
from ._fmu_input import load_parameters, get_realizations, find_surfaces, load_smry


__all__ = [
    "scratch_ensemble",
    "extract_mismatch",
    "load_surface",
    "get_wfence",
    "get_hfence",
    "extract_volumes",
    "load_parameters",
    "load_smry",
    "get_realizations",
    "find_surfaces",
]
