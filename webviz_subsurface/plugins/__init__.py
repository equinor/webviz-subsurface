"""These are plugins relevant within subsurface workflows. Most of them
rely on the setting `scratch_ensembles` within
`shared_settings`. This setting connects ensemble names (user defined)
with the paths to where the ensembles are stored, either absolute or
relative to the location of the configuration file.
I.e. you could have
```yaml
title: Reek Webviz Demonstration
shared_settings:
  scratch_ensembles:
    iter-0: /scratch/my_ensemble/realization-*/iter-0
    iter-1: /scratch/my_ensemble/realization-*/iter-1
pages:
  - title: Front page
    content:
      - plugin: ReservoirSimulationTimeSeries
        ensembles:
          - iter-0
          - iter-1
```
"""

from ._bhp_qc import BhpQc
from ._disk_usage import DiskUsage
from ._history_match import HistoryMatch
from ._horizon_uncertainty_viewer import HorizonUncertaintyViewer
from ._inplace_volumes import InplaceVolumes
from ._inplace_volumes_onebyone import InplaceVolumesOneByOne
from ._morris_plot import MorrisPlot
from ._parameter_analysis import ParameterAnalysis
from ._parameter_correlation import ParameterCorrelation
from ._parameter_distribution import ParameterDistribution
from ._parameter_parallel_coordinates import ParameterParallelCoordinates
from ._parameter_response_correlation import ParameterResponseCorrelation
from ._property_statistics import PropertyStatistics
from ._pvt_plot import PvtPlot
from ._relative_permeability import RelativePermeability
from ._reservoir_simulation_timeseries import ReservoirSimulationTimeSeries
from ._reservoir_simulation_timeseries_onebyone import (
    ReservoirSimulationTimeSeriesOneByOne,
)
from ._reservoir_simulation_timeseries_regional import (
    ReservoirSimulationTimeSeriesRegional,
)
from ._rft_plotter.rft_plotter import RftPlotter
from ._running_time_analysis_fmu import RunningTimeAnalysisFMU
from ._segy_viewer import SegyViewer
from ._subsurface_map import SubsurfaceMap
from ._surface_viewer_fmu import SurfaceViewerFMU
from ._surface_with_grid_cross_section import SurfaceWithGridCrossSection
from ._surface_with_seismic_cross_section import SurfaceWithSeismicCrossSection
from ._well_cross_section import WellCrossSection
from ._well_cross_section_fmu import WellCrossSectionFMU
from ._assisted_history_matching_analysis import AssistedHistoryMatchingAnalysis
