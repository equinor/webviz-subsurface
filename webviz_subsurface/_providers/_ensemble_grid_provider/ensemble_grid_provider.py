import abc
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Union

import numpy as np


# Class provides data for ensemble surfaces
class EnsembleGridProvider(abc.ABC):
    @abc.abstractmethod
    def provider_id(self) -> str:
        """Returns string ID of the provider."""

    @abc.abstractmethod
    def get_explicit_structured_grid_accessor(self, realization: int):
        """Returns the esg accessor"""

    @abc.abstractmethod
    def static_parameter_names(self) -> List[str]:
        """Returns list of all available static parameters."""

    @abc.abstractmethod
    def dynamic_parameter_names(self) -> List[str]:
        """Returns list of all available dynamic parameters."""

    @abc.abstractmethod
    def dates_for_dynamic_parameter(
        self, dynamic_parameter: str
    ) -> Optional[List[str]]:
        """Returns list of all available dates for a given dynamic parameter."""

    @abc.abstractmethod
    def realizations(self) -> List[int]:
        """Returns list of all available realizations."""

    @abc.abstractmethod
    def get_static_parameter_values(
        self, parameter_name: str, realization: int
    ) -> Optional[np.ndarray]:
        """Returns 1d values for a given static parameter"""

    @abc.abstractmethod
    def get_dynamic_parameter_values(
        self, parameter_name: str, parameter_date: str, realization: int
    ) -> Optional[np.ndarray]:
        """Returns 1d values for a given dynamic parameter"""
