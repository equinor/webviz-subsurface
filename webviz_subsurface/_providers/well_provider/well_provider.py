import abc
from dataclasses import dataclass
from typing import List

import numpy as np
import xtgeo


@dataclass(frozen=True)
class WellPath:
    x_arr: np.ndarray
    y_arr: np.ndarray
    z_arr: np.ndarray
    md_arr: np.ndarray


# Class provides data for wells
class WellProvider(abc.ABC):
    @abc.abstractmethod
    def provider_id(self) -> str:
        """Returns string ID of the provider."""

    @abc.abstractmethod
    def well_names(self) -> List[str]:
        """Returns list of all available well names."""

    @abc.abstractmethod
    def get_well_path(self, well_name: str) -> WellPath:
        """Returns the coordinates for the well path along with MD for the well."""

    @abc.abstractmethod
    def get_well_xtgeo_obj(self, well_name: str) -> xtgeo.Well:
        ...
