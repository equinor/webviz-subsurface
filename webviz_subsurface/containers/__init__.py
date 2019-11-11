"""### _Subsurface specific containers_

These are containers relevant within subsurface workflows. Most of them
rely on the setting `scratch_ensemble` configuration within the
`container_settings`.
I.e. you could have
```yaml
title: Reek Webviz Demonstration
username: some_username
password: some_password

container_settings:
  scratch_ensembles:
    iter-0: /scratch/my_ensemble/realization-*/iter-0
    iter-1: /scratch/my_ensemble/realization-*/iter-1

pages:

 - title: Front page
   content:
    - container: SummaryStats
      ensemble: iter-0
```
"""

from ._parameter_distribution import ParameterDistribution
from ._parameter_correlation import ParameterCorrelation
from ._disk_usage import DiskUsage
from ._subsurface_map import SubsurfaceMap
from ._history_match import HistoryMatch
from ._intersect import Intersect
from ._morris_plot import MorrisPlot
from ._inplace_volumes import InplaceVolumes
from ._inplace_volumes_onebyone import InplaceVolumesOneByOne
from ._reservoir_simulation_timeseries import ReservoirSimulationTimeSeries
from ._reservoir_simulation_timeseries_onebyone import (
    ReservoirSimulationTimeSeriesOneByOne,
)
from ._segy_viewer import SegyViewer


__all__ = [
    "ParameterDistribution",
    "ParameterCorrelation",
    "DiskUsage",
    "SubsurfaceMap",
    "HistoryMatch",
    "Intersect",
    "MorrisPlot",
    "InplaceVolumes",
    "InplaceVolumesOneByOne",
    "ReservoirSimulationTimeSeries",
    "ReservoirSimulationTimeSeriesOneByOne",
    "SegyViewer",
]
