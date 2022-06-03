import abc
import logging
from pathlib import Path
from typing import List, Optional, Set

import flask
from dataclasses import dataclass

from . import webviz_sumo

from webviz_subsurface._utils.perf_timer import PerfTimer

from .ensemble_surface_provider import EnsembleSurfaceProvider
from .ensemble_surface_provider_factory import EnsembleSurfaceProviderFactory

LOGGER = logging.getLogger(__name__)


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


class EnsembleProviderDealer_sumo(EnsembleProviderDealer):
    def __init__(self, use_session_token: bool) -> None:
        self._sumo_env = "dev"
        self._use_session_token = use_session_token

        self._hack_cache_case_to_sumo_id_dict = {}

    def field_names(self) -> List[str]:
        sumo = self._create_sumo_explorer()
        fields: dict = sumo.get_fields()
        return list(fields)

    def case_names(self, field_name: str) -> List[str]:
        if not isinstance(field_name, str):
            raise ValueError("field_name must be of type str")

        if self._hack_cache_case_to_sumo_id_dict:
            return list(self._hack_cache_case_to_sumo_id_dict)

        sumo = self._create_sumo_explorer()
        cases = sumo.get_cases(fields=[field_name])
        for case in cases:
            iteration_ids = case.get_iterations()
            if len(iteration_ids) > 0:
                case_name = case.case_name
                sumo_id_of_case = case.sumo_id
                self._hack_cache_case_to_sumo_id_dict[case_name] = sumo_id_of_case

        return list(self._hack_cache_case_to_sumo_id_dict)

    def iteration_ids(self, field_name: str, case_name: str) -> List[str]:
        if not isinstance(field_name, str):
            raise ValueError("field_name must be of type str")
        if not isinstance(case_name, str):
            raise ValueError("case_name must be of type str")

        case = self._get_sumo_case_obj(field_name, case_name)
        iteration_ids = case.get_iterations()
        return list(iteration_ids)

    def get_surface_provider(
        self, field_name: str, case_name: str, iteration_id: str
    ) -> Optional[EnsembleSurfaceProvider]:

        # Hack - builds cache
        if not self._hack_cache_case_to_sumo_id_dict:
            self.case_names(field_name)

        sumo_case_id = self._hack_cache_case_to_sumo_id_dict.get(case_name)
        if not sumo_case_id:
            return None

        access_token = None
        if self._use_session_token:
            access_token = flask.session.get("access_token")

        factory = EnsembleSurfaceProviderFactory.instance()
        return factory.create_from_sumo_case_id(
            sumo_id_of_case=sumo_case_id,
            iteration_id=iteration_id,
            use_access_token=self._use_session_token,
            access_token=access_token,
        )

    def _create_sumo_explorer(self) -> webviz_sumo.Explorer:
        if self._use_session_token:
            access_token = flask.session.get("access_token")
            return webviz_sumo.create_explorer(access_token)
        else:
            return webviz_sumo.create_interactive_explorer()

    def _get_sumo_case_obj(self, field_name: str, case_name: str) -> webviz_sumo.Case:
        sumo = self._create_sumo_explorer()

        # Hack - builds cache
        if not self._hack_cache_case_to_sumo_id_dict:
            self.case_names(field_name)

        sumo_case_id = self._hack_cache_case_to_sumo_id_dict[case_name]
        case = sumo.get_case_by_id(sumo_case_id)

        return case
