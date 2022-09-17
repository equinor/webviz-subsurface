import abc
from typing import List, Optional

import numpy as np
import xtgeo


class EnsembleGridProvider(abc.ABC):
    @abc.abstractmethod
    def provider_id(self) -> str:
        """Returns string ID of the provider."""

    @abc.abstractmethod
    def static_property_names(self) -> List[str]:
        """Returns list of all available static properties."""

    @abc.abstractmethod
    def dynamic_property_names(self) -> List[str]:
        """Returns list of all available dynamic properties."""

    @abc.abstractmethod
    def dates_for_dynamic_property(self, property_name: str) -> Optional[List[str]]:
        """Returns list of all available dates for a given dynamic property."""

    @abc.abstractmethod
    def realizations(self) -> List[int]:
        """Returns list of all available realizations."""

    @abc.abstractmethod
    def get_3dgrid(
        self,
        realization: int,
    ) -> xtgeo.Grid:
        """Returns grid for specified realization"""

    @abc.abstractmethod
    def get_static_property_values(
        self, property_name: str, realization: int
    ) -> Optional[np.ndarray]:
        """Returns 1d cell values for a given static property"""

    @abc.abstractmethod
    def get_dynamic_property_values(
        self, property_name: str, property_date: str, realization: int
    ) -> Optional[np.ndarray]:
        """Returns 1d cell values for a given dynamic property"""
