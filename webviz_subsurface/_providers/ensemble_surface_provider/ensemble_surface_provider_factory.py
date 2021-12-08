from enum import Enum

from fmu.ensemble import ScratchEnsemble
from webviz_config.webviz_factory import WebvizFactory
from webviz_config.webviz_factory_registry import WEBVIZ_FACTORY_REGISTRY
from webviz_config.webviz_instance_info import WebvizRunMode

from .ensemble_surface_provider import EnsembleSurfaceProvider
from ._provider_impl_file import EnsembleTableProviderImplArrow


class BackingType(Enum):
    FILE = "file"
    SUMO = "sumo"


class FMU(str, Enum):
    ENSEMBLE = "ENSEMBLE"
    REALIZATION = "REAL"


class FMUSurface(str, Enum):
    ATTRIBUTE = "attribute"
    NAME = "name"
    DATE = "date"
    TYPE = "type"


class SurfaceType(str, Enum):
    OBSERVED = "observed"
    SIMULATED = "simulated"


class SurfaceMode(str, Enum):
    MEAN = "Mean"
    REALIZATION = "Single realization"
    OBSERVED = "Observed"
    STDDEV = "StdDev"
    MINIMUM = "Minimum"
    MAXIMUM = "Maximum"
    P10 = "P10"
    P90 = "P90"


class EnsembleSurfaceProvider(WebvizFactory):
    pass
