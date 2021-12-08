import abc
import datetime
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence

import pandas as pd
import xtgeo

from .ensemble_surface_provider import EnsembleSurfaceProvider

# Class provides data for ensemble surfaces
class ProviderImplFileBased(EnsembleSurfaceProvider):
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
    def get_surface(self, surface) -> xtgeo.RegularSurface:
        """Returns a surface for a given surface context"""
        ...

    @abc.abstractmethod
    def _get_realization_surface(self, surface_context) -> xtgeo.RegularSurface:
        ...

    @abc.abstractmethod
    def _get_observation_surface(self, surface_context) -> xtgeo.RegularSurface:
        ...

    @abc.abstractmethod
    def _get_statistical_surface(self, surface_context) -> xtgeo.RegularSurface:
        ...
