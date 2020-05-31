"""### _Subsurface specific plugins_

These are plugins relevant within subsurface workflows. Most of them
rely on the setting `scratch_ensemble` configuration within the
`plugin_settings`.
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

from ._parameter_distribution import ParameterDistribution
from ._parameter_correlation import ParameterCorrelation
from ._parameter_response_correlation import ParameterResponseCorrelation
from ._disk_usage import DiskUsage
from ._subsurface_map import SubsurfaceMap
from ._history_match import HistoryMatch
from ._morris_plot import MorrisPlot
from ._inplace_volumes import InplaceVolumes
from ._inplace_volumes_onebyone import InplaceVolumesOneByOne
from ._reservoir_simulation_timeseries import ReservoirSimulationTimeSeries
from ._reservoir_simulation_timeseries_onebyone import (
    ReservoirSimulationTimeSeriesOneByOne,
)
from ._segy_viewer import SegyViewer
from ._surface_viewer_fmu import SurfaceViewerFMU
from ._surface_with_grid_cross_section import SurfaceWithGridCrossSection
from ._surface_with_seismic_cross_section import SurfaceWithSeismicCrossSection
from ._well_cross_section import WellCrossSection
from ._well_cross_section_fmu import WellCrossSectionFMU
from ._parameter_parallel_coordinates import ParameterParallelCoordinates
from ._running_time_analysis_fmu import RunningTimeAnalysisFMU
from ._relative_permeability import RelativePermeability
from ._reservoir_simulation_timeseries_regional import (
    ReservoirSimulationTimeSeriesRegional,
)
from ._rft_plotter.rft_plotter import RftPlotter


__all__ = [
    "ParameterDistribution",
    "ParameterCorrelation",
    "DiskUsage",
    "SubsurfaceMap",
    "HistoryMatch",
    "MorrisPlot",
    "InplaceVolumes",
    "InplaceVolumesOneByOne",
    "ReservoirSimulationTimeSeries",
    "ReservoirSimulationTimeSeriesOneByOne",
    "SegyViewer",
    "SurfaceViewerFMU",
    "SurfaceWithGridCrossSection",
    "SurfaceWithSeismicCrossSection",
    "WellCrossSection",
    "ParameterParallelCoordinates",
    "RunningTimeAnalysisFMU",
    "RelativePermeability",
    "ReservoirSimulationTimeSeriesRegional",
    "RftPlotter",
]
