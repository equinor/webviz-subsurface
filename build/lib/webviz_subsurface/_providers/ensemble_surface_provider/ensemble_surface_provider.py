import abc
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Union

import xtgeo


class SurfaceStatistic(str, Enum):
    MEAN = "Mean"
    STDDEV = "StdDev"
    MINIMUM = "Minimum"
    MAXIMUM = "Maximum"
    P10 = "P10"
    P90 = "P90"


@dataclass(frozen=True)
class StatisticalSurfaceAddress:
    """Specifies a unique statistical surface in an ensemble"""

    attribute: str
    name: str
    datestr: Optional[str]
    statistic: SurfaceStatistic
    realizations: List[int]


@dataclass(frozen=True)
class SimulatedSurfaceAddress:
    """Specifies a unique simulated surface for a given ensemble realization"""

    attribute: str
    name: str
    datestr: Optional[str]
    realization: int


@dataclass(frozen=True)
class ObservedSurfaceAddress:
    """Represents a unique observed surface"""

    attribute: str
    name: str
    datestr: Optional[str]


# Type aliases used for signature readability
SurfaceAddress = Union[
    StatisticalSurfaceAddress, SimulatedSurfaceAddress, ObservedSurfaceAddress
]

# Class provides data for ensemble surfaces
class EnsembleSurfaceProvider(abc.ABC):
    @abc.abstractmethod
    def provider_id(self) -> str:
        """Returns string ID of the provider."""

    @abc.abstractmethod
    def attributes(self) -> List[str]:
        """Returns list of all available attributes."""

    @abc.abstractmethod
    def surface_names_for_attribute(self, surface_attribute: str) -> List[str]:
        """Returns list of all available surface names for a given attribute."""

    @abc.abstractmethod
    def surface_dates_for_attribute(
        self, surface_attribute: str
    ) -> Optional[List[str]]:
        """Returns list of all available surface dates for a given attribute."""

    @abc.abstractmethod
    def realizations(self) -> List[int]:
        """Returns list of all available realizations."""

    @abc.abstractmethod
    def get_surface(
        self,
        address: SurfaceAddress,
    ) -> Optional[xtgeo.RegularSurface]:
        """Returns a surface for a given surface address"""

    # @abc.abstractmethod
    # def get_surface_bounds(self, surface: EnsembleSurfaceContext) -> List[float]:
    #     """Returns the bounds for a surface [xmin,ymin, xmax,ymax]"""

    # @abc.abstractmethod
    # def get_surface_value_range(self, surface: EnsembleSurfaceContext) -> List[float]:
    #     """Returns the value range for a given surface context [zmin, zmax]"""

    # @abc.abstractmethod
    # def get_surface_as_rgba(self, surface: EnsembleSurfaceContext) -> io.BytesIO:
    #     """Returns surface as a greyscale png RGBA with encoded elevation values
    #     in a bytestream"""
