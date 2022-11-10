import logging
import shutil
from enum import Enum
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd
import xtgeo

from webviz_subsurface._utils.perf_timer import PerfTimer

from ._egrid_file_discovery import EclipseCaseFileInfo
from .ensemble_grid_provider import EnsembleGridProvider

LOGGER = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class Col:
    REAL = "realization"
    EGRID = "egrid_path"
    INIT = "init_path"
    UNRST = "unrst_path"


class GridType(str, Enum):
    GEOMETRY = "geometry"
    STATIC_PROPERTY = "static_property"
    DYNAMIC_PROPERTY = "dynamic_property"


class ProviderImplEgrid(EnsembleGridProvider):
    def __init__(
        self,
        provider_id: str,
        provider_dir: Path,
        grid_inventory_df: pd.DataFrame,
        init_properties: List[str],
        restart_properties: List[str],
    ) -> None:
        self._provider_id = provider_id
        self._provider_dir = provider_dir
        self._inventory_df = grid_inventory_df
        self._init_properties = init_properties
        self._restart_properties = restart_properties
        first_unrst = self._inventory_df[Col.UNRST][0]
        self._restart_dates = [
            str(dateint)
            for dateint in xtgeo.GridProperties.scan_dates(
                str(provider_dir / first_unrst), datesonly=True
            )
        ]

    @staticmethod
    def write_backing_store(
        storage_dir: Path,
        storage_key: str,
        eclipse_case_paths: List[EclipseCaseFileInfo],
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
        LOGGER.info(f"Writing grid data backing store to: {provider_dir}")
        provider_dir.mkdir(parents=True, exist_ok=True)

        ecl_stored_cases = []
        for ecl_case in eclipse_case_paths:

            if do_copy_grid_data_into_store:

                egrid_rel_path = (
                    f"{ecl_case.realization}-{Path(ecl_case.egrid_path).name}"
                )
                init_rel_path = (
                    f"{ecl_case.realization}-{Path(ecl_case.init_path).name}"
                )
                unrst_rel_path = (
                    f"{ecl_case.realization}-{Path(ecl_case.unrst_path).name}"
                )
                ecl_stored_cases.append(
                    EclipseCaseFileInfo(
                        realization=ecl_case.realization,
                        egrid_path=egrid_rel_path,
                        init_path=init_rel_path,
                        unrst_path=unrst_rel_path,
                    )
                )

                shutil.copyfile(ecl_case.egrid_path, provider_dir / egrid_rel_path)
                shutil.copyfile(ecl_case.init_path, provider_dir / init_rel_path)
                shutil.copyfile(ecl_case.unrst_path, provider_dir / unrst_rel_path)

            else:
                ecl_stored_cases.append(ecl_case)

        timer.lap_s()

        grid_inventory_df = pd.DataFrame(ecl_stored_cases)

        parquet_file_name = provider_dir / "grid_inventory.parquet"

        grid_inventory_df.to_parquet(path=parquet_file_name)

    @staticmethod
    def from_backing_store(
        storage_dir: Path,
        storage_key: str,
        init_properties: List[str],
        restart_properties: List[str],
    ) -> Optional["ProviderImplEgrid"]:

        provider_dir = storage_dir / storage_key
        parquet_file_name = provider_dir / "grid_inventory.parquet"

        try:
            grid_inventory_df = pd.read_parquet(path=parquet_file_name)

            return ProviderImplEgrid(
                storage_key,
                provider_dir,
                grid_inventory_df,
                init_properties,
                restart_properties,
            )

        except FileNotFoundError:
            return None

    def provider_id(self) -> str:
        return self._provider_id

    def static_property_names(self) -> List[str]:
        return self._init_properties

    def dynamic_property_names(self) -> List[str]:
        return self._restart_properties

    def dates_for_dynamic_property(self, property_name: str) -> Optional[List[str]]:
        return self._restart_dates

    def realizations(self) -> List[int]:
        unique_reals = self._inventory_df[Col.REAL].unique()

        # Sort and strip out any entries with real == -1
        return sorted([r for r in unique_reals if r >= 0])

    def get_3dgrid(self, realization: int) -> xtgeo.Grid:

        df = self._inventory_df.loc[self._inventory_df[Col.REAL] == realization]
        df = df[Col.EGRID]
        grid = xtgeo.grid_from_file(self._provider_dir / df.iloc[0], fformat="egrid")

        return grid

    def get_static_property_values(
        self, property_name: str, realization: int
    ) -> Optional[np.ndarray]:
        grid = self.get_3dgrid(realization)
        df = self._inventory_df.loc[self._inventory_df[Col.REAL] == realization]
        df = df[Col.INIT]
        grid_property = xtgeo.gridproperty_from_file(
            self._provider_dir / df.iloc[0],
            fformat="init",
            name=property_name,
            grid=grid,
        )
        fill_value = np.nan if not grid_property.isdiscrete else -1

        return grid_property.get_npvalues1d(order="F", fill_value=fill_value).ravel()

    def get_dynamic_property_values(
        self, property_name: str, property_date: str, realization: int
    ) -> Optional[np.ndarray]:
        grid = self.get_3dgrid(realization)
        df = self._inventory_df.loc[self._inventory_df[Col.REAL] == realization]
        df = df[Col.UNRST]
        grid_property = xtgeo.gridproperty_from_file(
            self._provider_dir / df.iloc[0],
            fformat="unrst",
            name=property_name,
            date=property_date,
            grid=grid,
        )
        return grid_property.get_npvalues1d(order="F").ravel()
