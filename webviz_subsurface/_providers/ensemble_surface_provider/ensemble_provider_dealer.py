import abc
from dataclasses import dataclass
from typing import List, Optional

from .ensemble_surface_provider import EnsembleSurfaceProvider


@dataclass(frozen=True)
class ProviderInfo:
    field: str
    case: str
    iter_id: str
    provider_id: str


#
# Mapping from field + case + iter_id => ensemble name
#


class EnsembleProviderDealer(abc.ABC):
    #
    # These top three methods don't really belong here
    # They are more general and really pertain to general ensemble discovery in SUMO
    #
    @abc.abstractmethod
    def field_names(self) -> List[str]:
        pass

    @abc.abstractmethod
    def case_names(self, field_name: str) -> List[str]:
        pass

    @abc.abstractmethod
    def iteration_ids(self, field_name: str, case_name: str) -> List[str]:
        pass

    # For now, but will not be fully qualifying if backed by file based providers
    @abc.abstractmethod
    def get_surface_provider(
        self, field_name: str, case_name: str, iteration_id: str
    ) -> Optional[EnsembleSurfaceProvider]:
        pass

    # @abc.abstractmethod
    # def available_providers(self, field_name: Optional[str], case_name: Optional[str]) -> List[ProviderInfo]:

    # @abc.abstractmethod
    # def get_provider(self, provider_id: str) -> Optional[EnsembleSurfaceProvider]:
