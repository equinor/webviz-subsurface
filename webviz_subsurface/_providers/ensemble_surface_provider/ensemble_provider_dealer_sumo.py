import logging
from typing import List, Optional, Dict
from dataclasses import dataclass

import flask
import flask_caching

from webviz_subsurface._utils.perf_timer import PerfTimer

from . import webviz_sumo
from . import cache_helpers
from .ensemble_provider_dealer import EnsembleProviderDealer
from .ensemble_surface_provider import EnsembleSurfaceProvider
from .ensemble_surface_provider_factory import EnsembleSurfaceProviderFactory

from webviz_config.webviz_instance_info import WEBVIZ_INSTANCE_INFO

LOGGER = logging.getLogger(__name__)


class WorkSession:
    def __init__(
        self, cache: flask_caching.SimpleCache, use_session_token: bool
    ) -> None:
        self._use_session_token = use_session_token
        self._cache = cache
        self._cache_prefix = f"sumo_dealer:"
        self._sumo_explorer: Optional[webviz_sumo.Explorer] = None

    def _get_case_to_sumo_id_dict(self, field_name: str) -> Dict[str, str]:
        timer = PerfTimer()

        cache_key = self._cache_prefix + f"{field_name}:case_to_sumo_id_dict"
        case_to_sumo_id_dict: Dict[str, str] = self._cache.get(cache_key)
        if case_to_sumo_id_dict is not None:
            return case_to_sumo_id_dict

        et_cache_s = timer.lap_s()

        sumo = self.get_sumo_explorer()
        cases = sumo.get_cases(fields=[field_name])
        case_to_sumo_id_dict = {}
        for case in cases:
            case_name = case.case_name
            sumo_id_of_case = case.sumo_id
            case_to_sumo_id_dict[case_name] = sumo_id_of_case

        et_sumo_s = timer.lap_s()

        self._cache.set(cache_key, case_to_sumo_id_dict)

        et_cache_s += timer.lap_s()

        LOGGER.debug(
            f"WorkSession._get_case_to_sumo_id_dict() took: {timer.elapsed_s():.2f}s ("
            f"cache={et_cache_s:.2f}s, sumo={et_sumo_s:.2f}s)"
        )

        return case_to_sumo_id_dict

    def get_field_names(self) -> List[str]:
        cache_key = self._cache_prefix + "field_list"
        fields_list: List[str] = self._cache.get(cache_key)
        if fields_list is not None:
            return fields_list

        sumo = self.get_sumo_explorer()
        fields_dict: dict = sumo.get_fields()
        fields_list = list(fields_dict)

        self._cache.set(cache_key, fields_list)

        return fields_list

    def get_case_names(self, field_name: str) -> List[str]:
        case_to_sumo_id_dict = self._get_case_to_sumo_id_dict(field_name)
        return list(case_to_sumo_id_dict)

    def get_iteration_ids(self, field_name: str, case_name: str) -> List[str]:
        timer = PerfTimer()

        cache_key = self._cache_prefix + f"{field_name}:{case_name}:iteration_ids"
        iteration_id_list: List[str] = self._cache.get(cache_key)
        if iteration_id_list is not None:
            return iteration_id_list

        et_cache_s = timer.lap_s()

        iteration_id_list = []
        sumo_case_id = self.get_sumo_case_id(field_name, case_name)
        if sumo_case_id is not None:
            sumo = self.get_sumo_explorer()
            case = sumo.get_case_by_id(sumo_case_id)
            if case is not None:
                iteration_id_list = list(case.get_iterations())

        et_sumo_s = timer.lap_s()

        self._cache.set(cache_key, iteration_id_list)

        et_cache_s += timer.lap_s()

        LOGGER.debug(
            f"WorkSession.get_iteration_ids() took: {timer.elapsed_s():.2f}s ("
            f"cache={et_cache_s:.2f}s, sumo={et_sumo_s:.2f}s) "
        )

        return iteration_id_list

    def get_sumo_case_id(self, field_name: str, case_name: str) -> Optional[str]:
        case_to_sumo_id_dict = self._get_case_to_sumo_id_dict(field_name)
        sumo_case_id = case_to_sumo_id_dict.get(case_name)
        if sumo_case_id is not None:
            return sumo_case_id

        return None

    def get_sumo_explorer(self) -> webviz_sumo.Explorer:
        if self._sumo_explorer is not None:
            return self._sumo_explorer

        if self._use_session_token:
            access_token = self.get_access_token()
            self._sumo_explorer = webviz_sumo.create_explorer(access_token)
            print("using token")
            print(access_token)
        else:
            self._sumo_explorer = webviz_sumo.create_interactive_explorer()
            print("not using token")

        return self._sumo_explorer

    def get_access_token(self) -> str:
        if not self._use_session_token:
            raise ValueError("Cannot get access token when _use_session_token is False")

        access_token = flask.session.get("access_token")
        if not access_token:
            raise ValueError("Unable to get access token from flask session")

        return access_token


class EnsembleProviderDealerSumo(EnsembleProviderDealer):
    def __init__(self, use_session_token: bool) -> None:
        self._use_session_token = use_session_token
        self._cache = cache_helpers.get_or_create_cache()

    def field_names(self) -> List[str]:
        timer = PerfTimer()

        work_session = WorkSession(self._cache, self._use_session_token)
        field_names = work_session.get_field_names()
        LOGGER.debug(
            f"EnsembleProviderDealerSumo.field_names() took: {timer.elapsed_s():.2f}s"
        )

        return field_names

    def case_names(self, field_name: str) -> List[str]:
        if not isinstance(field_name, str):
            raise ValueError("field_name must be of type str")

        timer = PerfTimer()

        work_session = WorkSession(self._cache, self._use_session_token)
        case_names = work_session.get_case_names(field_name)
        LOGGER.debug(
            f"EnsembleProviderDealerSumo.case_names() took: {timer.elapsed_s():.2f}s"
        )

        return case_names

    def iteration_ids(self, field_name: str, case_name: str) -> List[str]:
        if not isinstance(field_name, str):
            raise ValueError("field_name must be of type str")
        if not isinstance(case_name, str):
            raise ValueError("case_name must be of type str")

        timer = PerfTimer()

        work_session = WorkSession(self._cache, self._use_session_token)
        iter_ids = work_session.get_iteration_ids(field_name, case_name)
        LOGGER.debug(
            f"EnsembleProviderDealerSumo.iteration_ids() took: {timer.elapsed_s():.2f}s"
        )

        return iter_ids

    def get_surface_provider(
        self, field_name: str, case_name: str, iteration_id: str
    ) -> Optional[EnsembleSurfaceProvider]:
        if not isinstance(field_name, str):
            raise ValueError("field_name must be of type str")
        if not isinstance(case_name, str):
            raise ValueError("case_name must be of type str")
        if not isinstance(case_name, (str, int)):
            raise ValueError("iteration_id must be of type str or int")

        timer = PerfTimer()

        work_session = WorkSession(self._cache, self._use_session_token)
        sumo_id = work_session.get_sumo_case_id(field_name, case_name)
        if sumo_id is None:
            return None

        access_token = None
        if self._use_session_token:
            access_token = work_session.get_access_token()

        factory = EnsembleSurfaceProviderFactory.instance()
        provider = factory.create_from_sumo_case_id(
            sumo_id_of_case=sumo_id,
            iteration_id=iteration_id,
            use_access_token=self._use_session_token,
            access_token=access_token,
        )

        LOGGER.debug(
            f"EnsembleProviderDealerSumo.get_surface_provider() took: {timer.elapsed_s():.2f}s"
        )

        return provider
