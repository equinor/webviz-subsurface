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


from ._grid_fmu_standard_discovery import GridFileInfo,GridParameterFileInfo
from .ensemble_grid_provider import EnsembleGridProvider


LOGGER = logging.getLogger(__name__)

REm"
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


class ProviderImplFile(EnsembleGridProvider):
    def __init__(
        self, provider_id: str, provider_dir: Path, surface_inventory_df: pd.DataFrame
    ) -> None:
        self._provider_id = provider_id
        self._provider_dir = provider_dir
        self._inventory_df = surface_inventory_df

    @staticmethod
    # pylint: disable=too-many-locals
    def write_backing_store(
        storage_dir: Path,
        storage_key: str,
        grids: List[GridFileInfo],
        grid_parameters: List[GridParameterFileInfo],
        avoid_copying_grid_data: bool,
    ) -> None:
        """If avoid_copying_grid_data if True, the specified grid data will NOT be copied
        into the backing store, but will be referenced from their source locations.
        Note that this is only useful when running in non-portable mode and will fail
        in portable mode.
        """

        timer = PerfTimer()

        do_copy_grid_data_into_store = not avoid_copying_grid_data

        # All data for this provider will be stored inside a sub-directory
        # given by the storage key
        provider_dir = storage_dir / storage_key
        LOGGER.debug(f"Writing grid data backing store to: {provider_dir}")
        provider_dir.mkdir(parents=True, exist_ok=True)

        type_arr: List[SurfaceType] = []
        real_arr: List[int] = []
        attribute_arr: List[str] = []
        name_arr: List[str] = []
        datestr_arr: List[str] = []
        rel_path_arr: List[str] = []
        original_path_arr: List[str] = []
        gridnames = [grid.name for grid in grids]
        for grid_parameter_info in grid_parameters:
            if grid_parameter_info.name not in gridnames:
                continue
            name_arr.append(grid_parameter_info.name)
            real_arr.append(grid_parameter_info.real)
            attribute_arr.append(grid_parameter_info.attribute)
            datestr_arr.append(grid_parameter_info.datestr if grid_parameter_info.datestr else "")
            original_path_arr.append(grid_parameter_info.path)

            rel_path_in_store = ""
            if do_copy_grid_data_into_store:
                rel_path_in_store = _compose_rel_sim_surf_pathstr(
                    real=grid_parameter_info.real,
                    attribute=grid_parameter_info.attribute,
                    name=grid_parameter_info.name,
                    datestr=grid_parameter_info.datestr,
                    extension=Path(grid_parameter_info.path).suffix,
                )
            
            rel_path_arr.append(rel_path_in_store)


        timer.lap_s()
        if do_copy_grid_data_into_store:
            LOGGER.debug(
                f"Copying {len(original_path_arr)} surfaces into backing store..."
            )
            _copy_grid_parameters_into_provider_dir(
                original_path_arr, rel_path_arr, provider_dir
            )
        et_copy_s = timer.lap_s()

        grid_inventory_df = pd.DataFrame(
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
        grid_inventory_df.to_parquet(path=parquet_file_name)

        if do_copy_grid_data_into_store:
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
    def _get_simulated_surface(
        self, address: SimulatedSurfaceAddress
    ) -> Optional[xtgeo.RegularSurface]:
        """Returns a Xtgeo surface instance of a single realization surface"""

        timer = PerfTimer()

        surf_fns: List[str] = self._locate_grid_paramters(
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

    def _locate_grid_paramters(
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

def _copy_grid_parameters_into_provider_dir(
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
    return str(Path(fname))

