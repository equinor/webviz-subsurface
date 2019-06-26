'''### _Subsurface data input_
Contains data processing functions used in the containers.
Some of the scripts are dependent on FMU postprocessing scripts
that will be made open source in the near future.
'''

from ._history_match import extract_mismatch, scratch_ensemble
from ._intersect import (make_well_trace, make_surface_traces,
                         make_cube_trace, make_param_trace, well_to_df,
                         surface_to_df, get_file_paths, get_realizations)
from ._summary_stats import get_summary_data, get_summary_stats

__all__ = ['scratch_ensemble',
           'extract_mismatch',
           'make_well_trace',
           'make_surface_traces',
           'make_cube_trace',
           'make_param_trace',
           'well_to_df',
           'surface_to_df',
           'get_file_paths',
           'get_realizations',
           '_summary_stats',
           ]
