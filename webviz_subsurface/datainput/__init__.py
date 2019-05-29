'''### _Subsurface data input_
Contains data processing functions used in the containers.
Some of the scripts are dependent on FMU postprocessing scripts
that will be made open source in the near future.
'''

from ._history_match import extract_mismatch, scratch_ensemble
from ._intersect import load_surface, get_wfence, get_hfence

__all__ = ['scratch_ensemble',
           'extract_mismatch',
           'load_surface',
           'get_wfence',
           'get_hfence']
