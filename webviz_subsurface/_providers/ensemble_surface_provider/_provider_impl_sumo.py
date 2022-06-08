import logging
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Set

import flask_caching
import xtgeo

from webviz_subsurface._utils.perf_timer import PerfTimer

from . import webviz_sumo
from ._stat_surf_cache import StatSurfCache
from .ensemble_surface_provider import (
    EnsembleSurfaceProvider,
    ObservedSurfaceAddress,
    SimulatedSurfaceAddress,
    StatisticalSurfaceAddress,
    SurfaceAddress,
    SurfaceStatistic,
)

LOGGER = logging.getLogger(__name__)


class ProviderImplSumo(EnsembleSurfaceProvider):
    def __init__(
        self,
        cache_dir: Path,
        cache: flask_caching.SimpleCache,
        sumo_id_of_case: str,
        iteration_id: str,
        use_access_token: bool,
        access_token: Optional[str],
    ) -> None:
        self._provider_id = f"sumo_{sumo_id_of_case}__{iteration_id}"
        self._case_sumo_id = sumo_id_of_case
        self._iteration_id = iteration_id
        self._use_access_token = use_access_token
        self._access_token = access_token

        self._cache_prefix = f"ProviderImplSumo_{self._provider_id}__"
        self._cache = cache

        # my_cache_dir = cache_dir / Path(
        #     "ProviderImplSumo_StatSurfCache_" + self._provider_id
        # )
        # self._stat_surf_cache = StatSurfCache(my_cache_dir)

    def provider_id(self) -> str:
        return self._provider_id

    def attributes(self) -> List[str]:
        timer = PerfTimer()

        cache_key = f"{self._cache_prefix}__attributes"
        cached_arr = self._cache.get(cache_key)
        if cached_arr is not None:
            LOGGER.debug(f"attributes() from cache in: {timer.elapsed_s():.2f}s")
            return cached_arr

        case = self._get_my_sumo_case()
        attrib_names = case.get_object_property_values(
            "tag_name", "surface", iteration_ids=[self._iteration_id]
        )
        attrib_names = sorted(attrib_names)

        self._cache.set(cache_key, attrib_names)

        LOGGER.debug(f"attributes() completed using Sumo in: {timer.elapsed_s():.2f}s")

        return attrib_names

    def surface_names_for_attribute(self, surface_attribute: str) -> List[str]:
        timer = PerfTimer()

        cache_key = (
            f"{self._cache_prefix}__surface_names_for_attribute_{surface_attribute}"
        )
        cached_arr = self._cache.get(cache_key)
        if cached_arr is not None:
            LOGGER.debug(
                f"surface_names_for_attribute({surface_attribute}) from cache in: {timer.elapsed_s():.2f}s"
            )
            return cached_arr

        case = self._get_my_sumo_case()
        surf_names = case.get_object_property_values(
            "object_name",
            "surface",
            iteration_ids=[self._iteration_id],
            tag_names=[surface_attribute],
        )
        surf_names = sorted(surf_names)

        self._cache.set(cache_key, surf_names)

        LOGGER.debug(
            f"surface_names_for_attribute({surface_attribute}) completed using Sumo in: {timer.elapsed_s():.2f}s"
        )

        return surf_names

    def surface_dates_for_attribute(
        self, surface_attribute: str
    ) -> Optional[List[str]]:
        timer = PerfTimer()

        cache_key = (
            f"{self._cache_prefix}__surface_dates_for_attribute_{surface_attribute}"
        )
        cached_arr = self._cache.get(cache_key)
        if cached_arr is not None:
            LOGGER.debug(
                f"surface_dates_for_attribute({surface_attribute}) from cache in: {timer.elapsed_s():.2f}s"
            )
            if len(cached_arr) == 1 and not bool(cached_arr[0]):
                return None
            return cached_arr

        case = self._get_my_sumo_case()
        time_intervals = case.get_object_property_values(
            "time_interval",
            "surface",
            iteration_ids=[self._iteration_id],
            tag_names=[surface_attribute],
        )

        datestr_arr: List[str] = []
        for interval_str in time_intervals:
            datestr_arr.append(interval_str if interval_str != "NULL" else "")

        datestr_arr = sorted(datestr_arr)

        self._cache.set(cache_key, datestr_arr)

        LOGGER.debug(
            f"surface_dates_for_attribute({surface_attribute}) completed using Sumo in: {timer.elapsed_s():.2f}s"
        )

        if len(datestr_arr) == 1 and not bool(datestr_arr[0]):
            return None

        return datestr_arr

    def realizations(self) -> List[int]:
        timer = PerfTimer()

        cache_key = f"{self._cache_prefix}__realizations"
        cached_arr = self._cache.get(cache_key)
        if cached_arr is not None:
            LOGGER.debug(f"realizations() from cache in: {timer.elapsed_s():.2f}s")
            return cached_arr

        case = self._get_my_sumo_case()
        realization_ids = case.get_object_property_values("realization_id", "surface")
        realization_ids = sorted(realization_ids)

        self._cache.set(cache_key, realization_ids)

        LOGGER.debug(
            f"realizations() completed using Sumo in: {timer.elapsed_s():.2f}s"
        )

        return realization_ids

    def get_surface(
        self,
        address: SurfaceAddress,
    ) -> Optional[xtgeo.RegularSurface]:
        if isinstance(address, StatisticalSurfaceAddress):
            return self._get_statistical_surface(address)
        if isinstance(address, SimulatedSurfaceAddress):
            return self._get_simulated_surface(address)
        if isinstance(address, ObservedSurfaceAddress):
            return None

        raise TypeError("Unknown type of surface address")

    def _get_my_sumo_case(self) -> webviz_sumo.Case:
        timer = PerfTimer()

        if self._use_access_token:
            sumo = webviz_sumo.create_explorer(self._access_token)
            print("using token from provider implementation")
            print(self._access_token)
        else:
            sumo = webviz_sumo.create_interactive_explorer()
            print("not using token from provider implementation")
        et_create_s = timer.lap_s()

        case = sumo.get_case_by_id(self._case_sumo_id)
        et_get_s = timer.lap_s()

        LOGGER.debug(
            f"_get_my_sumo_case() took: {timer.elapsed_s():.2f}s "
            f"(create={et_create_s:.2f}s, get={et_get_s:.2f}s)"
        )

        return case

    def _get_simulated_surface(
        self, address: SimulatedSurfaceAddress
    ) -> Optional[xtgeo.RegularSurface]:
        """Returns a Xtgeo surface instance of a single realization surface"""

        timer = PerfTimer()

        case = self._get_my_sumo_case()

        time_intervals_list = [address.datestr] if address.datestr is not None else []

        surface_collection = case.get_objects(
            "surface",
            iteration_ids=[self._iteration_id],
            realization_ids=[address.realization],
            tag_names=[address.attribute],
            object_names=[address.name],
            time_intervals=time_intervals_list,
        )

        num_surfaces = len(surface_collection)
        if num_surfaces == 0:
            LOGGER.warning(f"No simulated surface found in Sumo for {address}")
            return None
        if num_surfaces > 1:
            LOGGER.warning(
                f"Multiple simulated surfaces found in Sumo for: {address}"
                "Returning first surface."
            )

        surf = surface_collection[0]
        blob_bytes: bytes = surf.blob
        byte_stream = BytesIO(blob_bytes)
        xtgeo_surf = xtgeo.surface_from_file(byte_stream)

        LOGGER.debug(f"Loaded simulated surface from Sumo in: {timer.elapsed_s():.2f}s")

        return xtgeo_surf

    def _get_statistical_surface(
        self, address: StatisticalSurfaceAddress
    ) -> Optional[xtgeo.RegularSurface]:

        timer = PerfTimer()

        case = self._get_my_sumo_case()

        time_intervals_list = [address.datestr] if address.datestr is not None else []

        surface_collection = case.get_objects(
            "surface",
            iteration_ids=[self._iteration_id],
            realization_ids=address.realizations,
            tag_names=[address.attribute],
            object_names=[address.name],
            time_intervals=time_intervals_list,
        )

        surf_count = len(surface_collection)
        if surf_count == 0:
            LOGGER.warning(f"No simulated surfaces found in Sumo for {address}")
            return None

        surfstat_to_sumostatstr_map = {
            SurfaceStatistic.MEAN: "MEAN",
            SurfaceStatistic.STDDEV: "STD",
            SurfaceStatistic.MINIMUM: "MIN",
            SurfaceStatistic.MAXIMUM: "MAX",
            SurfaceStatistic.P10: "P10",
            SurfaceStatistic.P90: "P90",
        }
        sumo_aggr_str = surfstat_to_sumostatstr_map[address.statistic]

        agg_surf_bytes: bytes = surface_collection.aggregate(sumo_aggr_str)
        byte_stream = BytesIO(agg_surf_bytes)
        xtgeo_surf = xtgeo.surface_from_file(byte_stream)

        LOGGER.debug(
            f"Calculated statistical surface using Sumo in: {timer.elapsed_s():.2f}s ("
            f"[#surfaces={surf_count}, stat={address.statistic}, "
            f"attr={address.attribute}, name={address.name}, date={address.datestr}]"
        )

        return xtgeo_surf
