import logging
import shutil
import warnings
from enum import Enum
from pathlib import Path
from typing import List, Optional, Set

import numpy as np
import pandas as pd
import xtgeo

from webviz_subsurface._utils.perf_timer import PerfTimer

from ._stat_surf_cache import StatSurfCache
from ._surface_discovery import SurfaceFileInfo
from .ensemble_surface_provider import (
    EnsembleSurfaceProvider,
    ObservedSurfaceAddress,
    SimulatedSurfaceAddress,
    StatisticalSurfaceAddress,
    SurfaceAddress,
    SurfaceStatistic,
)

LOGGER = logging.getLogger(__name__)

REL_SIM_DIR = "sim"
REL_OBS_DIR = "obs"
REL_STAT_CACHE_DIR = "stat_cache"

# pylint: disable=too-few-public-methods
class Col:
    TYPE = "type"
    REAL = "real"
    ATTRIBUTE = "attribute"
    NAME = "name"
    DATESTR = "datestr"
    ORIGINAL_PATH = "original_path"
    REL_PATH = "rel_path"


class SurfaceType(str, Enum):
    OBSERVED = "observed"
    SIMULATED = "simulated"


class ProviderImplFile(EnsembleSurfaceProvider):
    def __init__(
        self, provider_id: str, provider_dir: Path, surface_inventory_df: pd.DataFrame
    ) -> None:
        self._provider_id = provider_id
        self._provider_dir = provider_dir
        self._inventory_df = surface_inventory_df

        self._stat_surf_cache = StatSurfCache(self._provider_dir / REL_STAT_CACHE_DIR)

    @staticmethod
    # pylint: disable=too-many-locals
    def write_backing_store(
        storage_dir: Path,
        storage_key: str,
        sim_surfaces: List[SurfaceFileInfo],
        obs_surfaces: List[SurfaceFileInfo],
        avoid_copying_surfaces: bool,
    ) -> None:
        """If avoid_copying_surfaces if True, the specified surfaces will NOT be copied
        into the backing store, but will be referenced from their source locations.
        Note that this is only useful when running in non-portable mode and will fail
        in portable mode.
        """

        timer = PerfTimer()

        do_copy_surfs_into_store = not avoid_copying_surfaces

        # All data for this provider will be stored inside a sub-directory
        # given by the storage key
        provider_dir = storage_dir / storage_key
        LOGGER.debug(f"Writing surface backing store to: {provider_dir}")
        provider_dir.mkdir(parents=True, exist_ok=True)
        (provider_dir / REL_SIM_DIR).mkdir(parents=True, exist_ok=True)
        (provider_dir / REL_OBS_DIR).mkdir(parents=True, exist_ok=True)

        type_arr: List[SurfaceType] = []
        real_arr: List[int] = []
        attribute_arr: List[str] = []
        name_arr: List[str] = []
        datestr_arr: List[str] = []
        rel_path_arr: List[str] = []
        original_path_arr: List[str] = []

        for surfinfo in sim_surfaces:
            type_arr.append(SurfaceType.SIMULATED)
            real_arr.append(surfinfo.real)
            attribute_arr.append(surfinfo.attribute)
            name_arr.append(surfinfo.name)
            datestr_arr.append(surfinfo.datestr if surfinfo.datestr else "")
            original_path_arr.append(surfinfo.path)

            rel_path_in_store = ""
            if do_copy_surfs_into_store:
                rel_path_in_store = _compose_rel_sim_surf_pathstr(
                    real=surfinfo.real,
                    attribute=surfinfo.attribute,
                    name=surfinfo.name,
                    datestr=surfinfo.datestr,
                    extension=Path(surfinfo.path).suffix,
                )
            rel_path_arr.append(rel_path_in_store)

        # We want to strip out observed surfaces without a matching simulated surface
        valid_obs_surfaces = _find_observed_surfaces_corresponding_to_simulated(
            obs_surfaces=obs_surfaces, sim_surfaces=sim_surfaces
        )

        for surfinfo in valid_obs_surfaces:
            type_arr.append(SurfaceType.OBSERVED)
            real_arr.append(-1)
            attribute_arr.append(surfinfo.attribute)
            name_arr.append(surfinfo.name)
            datestr_arr.append(surfinfo.datestr if surfinfo.datestr else "")
            original_path_arr.append(surfinfo.path)

            rel_path_in_store = ""
            if do_copy_surfs_into_store:
                rel_path_in_store = _compose_rel_obs_surf_pathstr(
                    attribute=surfinfo.attribute,
                    name=surfinfo.name,
                    datestr=surfinfo.datestr,
                    extension=Path(surfinfo.path).suffix,
                )
            rel_path_arr.append(rel_path_in_store)

        timer.lap_s()
        if do_copy_surfs_into_store:
            LOGGER.debug(
                f"Copying {len(original_path_arr)} surfaces into backing store..."
            )
            _copy_surfaces_into_provider_dir(
                original_path_arr, rel_path_arr, provider_dir
            )
        et_copy_s = timer.lap_s()

        surface_inventory_df = pd.DataFrame(
            {
                Col.TYPE: type_arr,
                Col.REAL: real_arr,
                Col.ATTRIBUTE: attribute_arr,
                Col.NAME: name_arr,
                Col.DATESTR: datestr_arr,
                Col.REL_PATH: rel_path_arr,
                Col.ORIGINAL_PATH: original_path_arr,
            }
        )

        parquet_file_name = provider_dir / "surface_inventory.parquet"
        surface_inventory_df.to_parquet(path=parquet_file_name)

        if do_copy_surfs_into_store:
            LOGGER.debug(
                f"Wrote surface backing store in: {timer.elapsed_s():.2f}s ("
                f"copy={et_copy_s:.2f}s)"
            )
        else:
            LOGGER.debug(
                f"Wrote surface backing store without copying surfaces in: "
                f"{timer.elapsed_s():.2f}s"
            )

    @staticmethod
    def from_backing_store(
        storage_dir: Path,
        storage_key: str,
    ) -> Optional["ProviderImplFile"]:

        provider_dir = storage_dir / storage_key
        parquet_file_name = provider_dir / "surface_inventory.parquet"

        try:
            surface_inventory_df = pd.read_parquet(path=parquet_file_name)
            return ProviderImplFile(storage_key, provider_dir, surface_inventory_df)
        except FileNotFoundError:
            return None

    def provider_id(self) -> str:
        return self._provider_id

    def attributes(self) -> List[str]:
        return sorted(list(self._inventory_df[Col.ATTRIBUTE].unique()))

    def surface_names_for_attribute(self, surface_attribute: str) -> List[str]:
        return sorted(
            list(
                self._inventory_df.loc[
                    self._inventory_df[Col.ATTRIBUTE] == surface_attribute
                ][Col.NAME].unique()
            )
        )

    def surface_dates_for_attribute(
        self, surface_attribute: str
    ) -> Optional[List[str]]:
        dates = sorted(
            list(
                self._inventory_df.loc[
                    self._inventory_df[Col.ATTRIBUTE] == surface_attribute
                ][Col.DATESTR].unique()
            )
        )
        if len(dates) == 1 and not bool(dates[0]):
            return None

        return dates

    def realizations(self) -> List[int]:
        unique_reals = self._inventory_df[Col.REAL].unique()

        # Sort and strip out any entries with real == -1
        return sorted([r for r in unique_reals if r >= 0])

    def get_surface(
        self,
        address: SurfaceAddress,
    ) -> Optional[xtgeo.RegularSurface]:
        if isinstance(address, StatisticalSurfaceAddress):
            return self._get_or_create_statistical_surface(address)
            # return self._create_statistical_surface(address)
        if isinstance(address, SimulatedSurfaceAddress):
            return self._get_simulated_surface(address)
        if isinstance(address, ObservedSurfaceAddress):
            return self._get_observed_surface(address)

        raise TypeError("Unknown type of surface address")

    def _get_or_create_statistical_surface(
        self, address: StatisticalSurfaceAddress
    ) -> Optional[xtgeo.RegularSurface]:

        timer = PerfTimer()

        surf = self._stat_surf_cache.fetch(address)
        if surf:
            LOGGER.debug(
                f"Fetched statistical surface from cache in: {timer.elapsed_s():.2f}s"
            )
            return surf

        surf = self._create_statistical_surface(address)
        et_create_s = timer.lap_s()

        self._stat_surf_cache.store(address, surf)
        et_write_cache_s = timer.lap_s()

        LOGGER.debug(
            f"Created and wrote statistical surface to cache in: {timer.elapsed_s():.2f}s ("
            f"create={et_create_s:.2f}s, store={et_write_cache_s:.2f}s), "
            f"[stat={address.statistic}, "
            f"attr={address.attribute}, name={address.name}, date={address.datestr}]"
        )

        return surf

    def _create_statistical_surface(
        self, address: StatisticalSurfaceAddress
    ) -> Optional[xtgeo.RegularSurface]:
        surf_fns: List[str] = self._locate_simulated_surfaces(
            attribute=address.attribute,
            name=address.name,
            datestr=address.datestr if address.datestr is not None else "",
            realizations=address.realizations,
        )

        if len(surf_fns) == 0:
            LOGGER.warning(f"No input surfaces found for statistical surface {address}")
            return None

        timer = PerfTimer()

        surfaces = xtgeo.Surfaces(surf_fns)
        et_load_s = timer.lap_s()

        surf_count = len(surfaces.surfaces)
        if surf_count == 0:
            LOGGER.warning(
                f"Could not load input surfaces for statistical surface {address}"
            )
            return None

        # print("########################################################")
        # first_surf = surfaces.surfaces[0]
        # for surf in surfaces.surfaces:
        #     print(
        #         surf.dimensions,
        #         surf.xinc,
        #         surf.yinc,
        #         surf.xori,
        #         surf.yori,
        #         surf.rotation,
        #         surf.filesrc,
        #     )
        # print("########################################################")

        # Suppress numpy warnings when surfaces have undefined z-values
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", "All-NaN slice encountered")
            warnings.filterwarnings("ignore", "Mean of empty slice")
            warnings.filterwarnings("ignore", "Degrees of freedom <= 0 for slice")

            stat_surface = _calc_statistic_across_surfaces(address.statistic, surfaces)
        et_calc_s = timer.lap_s()

        LOGGER.debug(
            f"Created statistical surface in: {timer.elapsed_s():.2f}s ("
            f"load={et_load_s:.2f}s, calc={et_calc_s:.2f}s), "
            f"[#surfaces={surf_count}, stat={address.statistic}, "
            f"attr={address.attribute}, name={address.name}, date={address.datestr}]"
        )

        return stat_surface

    def _get_simulated_surface(
        self, address: SimulatedSurfaceAddress
    ) -> Optional[xtgeo.RegularSurface]:
        """Returns a Xtgeo surface instance of a single realization surface"""

        timer = PerfTimer()

        surf_fns: List[str] = self._locate_simulated_surfaces(
            attribute=address.attribute,
            name=address.name,
            datestr=address.datestr if address.datestr is not None else "",
            realizations=[address.realization],
        )

        if len(surf_fns) == 0:
            LOGGER.warning(f"No simulated surface found for {address}")
            return None
        if len(surf_fns) > 1:
            LOGGER.warning(
                f"Multiple simulated surfaces found for: {address}"
                "Returning first surface."
            )

        surf = xtgeo.surface_from_file(surf_fns[0])

        LOGGER.debug(f"Loaded simulated surface in: {timer.elapsed_s():.2f}s")

        return surf

    def _get_observed_surface(
        self, address: ObservedSurfaceAddress
    ) -> Optional[xtgeo.RegularSurface]:
        """Returns a Xtgeo surface instance for an observed surface"""

        timer = PerfTimer()

        surf_fns: List[str] = self._locate_observed_surfaces(
            attribute=address.attribute,
            name=address.name,
            datestr=address.datestr if address.datestr is not None else "",
        )

        if len(surf_fns) == 0:
            LOGGER.warning(f"No observed surface found for {address}")
            return None
        if len(surf_fns) > 1:
            LOGGER.warning(
                f"Multiple observed surfaces found for: {address}"
                "Returning first surface."
            )

        surf = xtgeo.surface_from_file(surf_fns[0])

        LOGGER.debug(f"Loaded simulated surface in: {timer.elapsed_s():.2f}s")

        return surf

    def _locate_simulated_surfaces(
        self, attribute: str, name: str, datestr: str, realizations: List[int]
    ) -> List[str]:
        """Returns list of file names matching the specified filter criteria"""
        df = self._inventory_df.loc[
            self._inventory_df[Col.TYPE] == SurfaceType.SIMULATED
        ]

        df = df.loc[
            (df[Col.ATTRIBUTE] == attribute)
            & (df[Col.NAME] == name)
            & (df[Col.DATESTR] == datestr)
            & (df[Col.REAL].isin(realizations))
        ]

        df = df[[Col.REL_PATH, Col.ORIGINAL_PATH]]

        # Return file name within backing store if the surface was copied there,
        # otherwise return the original source file name
        fn_list: List[str] = []
        for _index, row in df.iterrows():
            if row[Col.REL_PATH]:
                fn_list.append(self._provider_dir / row[Col.REL_PATH])
            else:
                fn_list.append(row[Col.ORIGINAL_PATH])

        return fn_list

    def _locate_observed_surfaces(
        self, attribute: str, name: str, datestr: str
    ) -> List[str]:
        """Returns file names of observed surfaces matching the criteria"""
        df = self._inventory_df.loc[
            self._inventory_df[Col.TYPE] == SurfaceType.OBSERVED
        ]

        df = df.loc[
            (df[Col.ATTRIBUTE] == attribute)
            & (df[Col.NAME] == name)
            & (df[Col.DATESTR] == datestr)
        ]

        df = df[[Col.REL_PATH, Col.ORIGINAL_PATH]]

        # Return file name within backing store if the surface was copied there,
        # otherwise return the original source file name
        fn_list: List[str] = []
        for _index, row in df.iterrows():
            if row[Col.REL_PATH]:
                fn_list.append(self._provider_dir / row[Col.REL_PATH])
            else:
                fn_list.append(row[Col.ORIGINAL_PATH])

        return fn_list


def _find_observed_surfaces_corresponding_to_simulated(
    obs_surfaces: List[SurfaceFileInfo], sim_surfaces: List[SurfaceFileInfo]
) -> List[SurfaceFileInfo]:
    """Returns only the observed surfaces that have a matching simulated surface"""

    unique_sim_surf_ids: Set[str] = set()
    for surfinfo in sim_surfaces:
        surf_id = f"{surfinfo.name}_{surfinfo.attribute}_{surfinfo.datestr}"
        unique_sim_surf_ids.add(surf_id)

    valid_obs_surfaces: List[SurfaceFileInfo] = []
    for surfinfo in obs_surfaces:
        surf_id = f"{surfinfo.name}_{surfinfo.attribute}_{surfinfo.datestr}"
        if surf_id in unique_sim_surf_ids:
            valid_obs_surfaces.append(surfinfo)
        else:
            LOGGER.debug(
                f"Discarding observed surface without matching simulation surface {surfinfo.path}"
            )

    return valid_obs_surfaces


def _copy_surfaces_into_provider_dir(
    original_path_arr: List[str],
    rel_path_arr: List[str],
    provider_dir: Path,
) -> None:
    for src_path, dst_rel_path in zip(original_path_arr, rel_path_arr):
        # LOGGER.debug(f"copying surface from: {src_path}")
        shutil.copyfile(src_path, provider_dir / dst_rel_path)

    # full_dst_path_arr = [storage_dir / dst_rel_path for dst_rel_path in store_path_arr]
    # with ProcessPoolExecutor() as executor:
    #     executor.map(shutil.copyfile, original_path_arr, full_dst_path_arr)


def _compose_rel_sim_surf_pathstr(
    real: int,
    attribute: str,
    name: str,
    datestr: Optional[str],
    extension: str,
) -> str:
    """Compose path to simulated surface file, relative to provider's directory"""
    if datestr:
        fname = f"{real}--{name}--{attribute}--{datestr}{extension}"
    else:
        fname = f"{real}--{name}--{attribute}{extension}"
    return str(Path(REL_SIM_DIR) / fname)


def _compose_rel_obs_surf_pathstr(
    attribute: str,
    name: str,
    datestr: Optional[str],
    extension: str,
) -> str:
    """Compose path to observed surface file, relative to provider's directory"""
    if datestr:
        fname = f"{name}--{attribute}--{datestr}{extension}"
    else:
        fname = f"{name}--{attribute}{extension}"
    return str(Path(REL_OBS_DIR) / fname)


def _calc_statistic_across_surfaces(
    statistic: SurfaceStatistic, surfaces: xtgeo.Surfaces
) -> xtgeo.RegularSurface:
    """Calculates a statistical surface from a list of Xtgeo surface instances"""

    stat_surf: xtgeo.RegularSurface

    if statistic == SurfaceStatistic.MEAN:
        stat_surf = surfaces.apply(np.mean, axis=0)
    elif statistic == SurfaceStatistic.STDDEV:
        stat_surf = surfaces.apply(np.std, axis=0)
    elif statistic == SurfaceStatistic.MINIMUM:
        stat_surf = surfaces.apply(np.min, axis=0)
    elif statistic == SurfaceStatistic.MAXIMUM:
        stat_surf = surfaces.apply(np.max, axis=0)
    elif statistic == SurfaceStatistic.P10:
        stat_surf = surfaces.apply(np.percentile, 10, axis=0)
    elif statistic == SurfaceStatistic.P90:
        stat_surf = surfaces.apply(np.percentile, 90, axis=0)

    return stat_surf
