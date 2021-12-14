import abc
import io
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence

import pandas as pd
import xtgeo


class EnsembleSurfaceMode(str, Enum):
    MEAN = "Mean"
    REALIZATION = "Single realization"
    OBSERVED = "Observed"
    STDDEV = "StdDev"
    MINIMUM = "Minimum"
    MAXIMUM = "Maximum"
    P10 = "P10"
    P90 = "P90"


@dataclass(frozen=True)
class EnsembleSurfaceContext:
    """Represents a unique surface in an ensemble"""

    ensemble: str
    realizations: List[int]
    attribute: str
    date: Optional[str]
    name: str
    mode: EnsembleSurfaceMode


@dataclass(frozen=True)
class RealizationSurfaceContext:
    """Represents a unique surface for a given ensemble realization"""

    ensemble: str
    realization: int
    attribute: str
    name: str
    date: Optional[str]


@dataclass(frozen=True)
class ObservationSurfaceContext:
    """Represents a unique observed surface"""

    attribute: str
    name: str
    date: Optional[str]


# Class provides data for ensemble surfaces
class EnsembleSurfaceProvider(abc.ABC):
    @abc.abstractmethod
    @property
    def attributes(self) -> List[str]:
        """Returns list of all available attribute."""
        ...

    @abc.abstractmethod
    def surface_names_for_attribute(self, surface_attribute: str) -> List[str]:
        """Returns list of all available surface names for a given attribute."""
        ...

    @abc.abstractmethod
    def surface_dates_for_attribute(
        self, surface_attribute: str
    ) -> Optional[List[str]]:
        """Returns list of all available surface dates for a given attribute."""
        ...

    @abc.abstractmethod
    def realizations(self) -> List[int]:
        """Returns list of all available realizations."""
        ...

    @abc.abstractmethod
    def get_surface(self, surface: EnsembleSurfaceContext) -> xtgeo.RegularSurface:
        """Returns a surface for a given surface context"""
        ...

    @abc.abstractmethod
    def get_surface_bounds(self, surface: EnsembleSurfaceContext) -> List[float]:
        """Returns the bounds for a surface [xmin,ymin, xmax,ymax]"""
        ...

    @abc.abstractmethod
    def get_surface_value_range(self, surface: EnsembleSurfaceContext) -> List[float]:
        """Returns the value range for a given surface context [zmin, zmax]"""
        ...

    @abc.abstractmethod
    def get_surface_as_rgba(self, surface: EnsembleSurfaceContext) -> io.BytesIO:
        """Returns surface as a greyscale png RGBA with encoded elevation values
        in a bytestream"""
        ...

    @abc.abstractmethod
    def _get_realization_surface(
        self, surface_context: RealizationSurfaceContext
    ) -> xtgeo.RegularSurface:
        """Returns a surface for a single realization"""
        ...

    @abc.abstractmethod
    def _get_observation_surface(
        self, surface_context: ObservationSurfaceContext
    ) -> xtgeo.RegularSurface:
        """Returns an observed surface"""
        ...

    @abc.abstractmethod
    def _get_statistical_surface(
        self, surface_context: EnsembleSurfaceContext
    ) -> xtgeo.RegularSurface:
        """Returns a statistical surface over a set of realizations"""
        ...
