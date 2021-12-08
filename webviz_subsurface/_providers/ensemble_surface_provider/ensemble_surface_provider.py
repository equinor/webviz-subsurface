import abc
import datetime
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence

import pandas as pd
import xtgeo


class SurfaceMode(str, Enum):
    MEAN = "Mean"
    REALIZATION = "Single realization"
    OBSERVED = "Observed"
    STDDEV = "StdDev"
    MINIMUM = "Minimum"
    MAXIMUM = "Maximum"
    P10 = "P10"
    P90 = "P90"


@dataclass(frozen=True)
class SurfaceContext:
    ensemble: str
    realizations: List[int]
    attribute: str
    date: Optional[str]
    name: str
    mode: SurfaceMode


# Class provides data for ensemble surfaces
class EnsembleSurfaceProvider(abc.ABC):
    @abc.abstractmethod
    def surface_attributes(self) -> List[str]:
        """Returns list of all available attribute."""
        ...

    @abc.abstractmethod
    def surface_names_for_attribute(self, surface_attribute: str) -> List[str]:
        """Returns list of all available surface names for a given attribute."""
        ...

    @abc.abstractmethod
    def surface_dates_for_attribute(self, surface_attribute: str) -> List[str]:
        """Returns list of all available surface names for a given attribute."""
        ...

    @abc.abstractmethod
    def realizations(self) -> List[int]:
        """Returns list of all available realization numbers."""
        ...

    @abc.abstractmethod
    def get_surface(self, surface: SurfaceContext) -> xtgeo.RegularSurface:
        """Returns a surface for a given surface context"""
        ...

    @abc.abstractmethod
    def _get_realization_surface(
        self, surface_context: SurfaceContext
    ) -> xtgeo.RegularSurface:
        ...

    @abc.abstractmethod
    def _get_observation_surface(
        self, surface_context: SurfaceContext
    ) -> xtgeo.RegularSurface:
        ...

    @abc.abstractmethod
    def _get_statistical_surface(
        self, surface_context: SurfaceContext
    ) -> xtgeo.RegularSurface:
        ...
