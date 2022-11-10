import logging
import shutil
from enum import Enum
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd
import xtgeo

from webviz_subsurface._utils.perf_timer import PerfTimer

from ._roff_file_discovery import GridFileInfo, GridParameterFileInfo
from .ensemble_grid_provider import EnsembleGridProvider

LOGGER = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class Col:
    TYPE = "type"
    REAL = "real"
    ATTRIBUTE = "attribute"
    NAME = "name"
    DATESTR = "datestr"
    ORIGINAL_PATH = "original_path"
    REL_PATH = "rel_path"


class GridType(str, Enum):
    GEOMETRY = "geometry"
    STATIC_PROPERTY = "static_property"
    DYNAMIC_PROPERTY = "dynamic_property"


class ProviderImplRoff(EnsembleGridProvider):
    def __init__(
        self, provider_id: str, provider_dir: Path, grid_inventory_df: pd.DataFrame
    ) -> None:
        self._provider_id = provider_id
        self._provider_dir = provider_dir
        self._inventory_df = grid_inventory_df

    @staticmethod
    # pylint: disable=too-many-locals
    def write_backing_store(
        storage_dir: Path,
        storage_key: str,
        grid_geometries_info: List[GridFileInfo],
        grid_parameters_info: List[GridParameterFileInfo],
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

        type_arr: List[GridType] = []
        real_arr: List[int] = []
        attribute_arr: List[str] = []
        name_arr: List[str] = []
        datestr_arr: List[str] = []
        rel_path_arr: List[str] = []
        original_path_arr: List[str] = []
        for grid_info in grid_geometries_info:
            type_arr.append(GridType.GEOMETRY)
            name_arr.append(grid_info.name)
            real_arr.append(grid_info.real)
            attribute_arr.append("")
            datestr_arr.append("")
            original_path_arr.append(grid_info.path)
            rel_path_in_store = ""

            if do_copy_grid_data_into_store:
                rel_path_in_store = _compose_rel_grid_pathstr(
                    real=grid_info.real,
                    attribute=None,
                    name=grid_info.name,
                    datestr=None,
                    extension=Path(grid_info.path).suffix,
                )

            rel_path_arr.append(rel_path_in_store)

        for grid_parameter_info in grid_parameters_info:
            name_arr.append(grid_parameter_info.name)
            real_arr.append(grid_parameter_info.real)
            attribute_arr.append(grid_parameter_info.attribute)
            if grid_parameter_info.datestr:
                datestr_arr.append(grid_parameter_info.datestr)
                type_arr.append(GridType.DYNAMIC_PROPERTY)
            else:
                datestr_arr.append("")
                type_arr.append(GridType.STATIC_PROPERTY)

            original_path_arr.append(grid_parameter_info.path)

            rel_path_in_store = ""
            if do_copy_grid_data_into_store:
                rel_path_in_store = _compose_rel_grid_pathstr(
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
                f"Copying {len(original_path_arr)} grid data into backing store..."
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

        parquet_file_name = provider_dir / "grid_inventory.parquet"
        grid_inventory_df.to_parquet(path=parquet_file_name)

        if do_copy_grid_data_into_store:
            LOGGER.debug(
                f"Wrote grid backing store in: {timer.elapsed_s():.2f}s ("
                f"copy={et_copy_s:.2f}s)"
            )
        else:
            LOGGER.debug(
                f"Wrote grid backing store without copying grid data in: "
                f"{timer.elapsed_s():.2f}s"
            )

    @staticmethod
    def from_backing_store(
        storage_dir: Path,
        storage_key: str,
    ) -> Optional["ProviderImplRoff"]:

        provider_dir = storage_dir / storage_key
        parquet_file_name = provider_dir / "grid_inventory.parquet"

        try:
            grid_inventory_df = pd.read_parquet(path=parquet_file_name)
            return ProviderImplRoff(storage_key, provider_dir, grid_inventory_df)
        except FileNotFoundError:
            return None

    def provider_id(self) -> str:
        return self._provider_id

    def static_property_names(self) -> List[str]:
        return sorted(
            list(
                self._inventory_df.loc[
                    self._inventory_df[Col.TYPE] == GridType.STATIC_PROPERTY
                ][Col.ATTRIBUTE].unique()
            )
        )

    def dynamic_property_names(self) -> List[str]:
        return sorted(
            list(
                self._inventory_df.loc[
                    self._inventory_df[Col.TYPE] == GridType.DYNAMIC_PROPERTY
                ][Col.ATTRIBUTE].unique()
            )
        )

    def dates_for_dynamic_property(self, property_name: str) -> Optional[List[str]]:
        dates = sorted(
            list(
                self._inventory_df.loc[
                    (self._inventory_df[Col.TYPE] == GridType.DYNAMIC_PROPERTY)
                    & (self._inventory_df[Col.ATTRIBUTE] == property_name)
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

    def get_3dgrid(self, realization: int) -> xtgeo.Grid:
        df = self._inventory_df.loc[self._inventory_df[Col.TYPE] == GridType.GEOMETRY]
        df = df.loc[df[Col.REAL] == realization]

        df = df[[Col.REL_PATH, Col.ORIGINAL_PATH]]
        fn_list: List[str] = []
        for _index, row in df.iterrows():
            if row[Col.REL_PATH]:
                fn_list.append(self._provider_dir / row[Col.REL_PATH])
            else:
                fn_list.append(row[Col.ORIGINAL_PATH])
        if len(fn_list) == 0:
            LOGGER.warning(f"No grid geometry found for realization {realization}")
            return None
        if len(fn_list) > 1:
            raise ValueError(
                f"Multiple grid geometries found for: {realization}"
                "Something has gone terribly wrong."
            )

        grid = xtgeo.grid_from_file(fn_list[0])
        return grid

    def get_static_property_values(
        self, property_name: str, realization: int
    ) -> Optional[np.ndarray]:
        fn_list: List[str] = self._locate_static_property(
            property_name=property_name, realizations=[realization]
        )
        if len(fn_list) == 0:
            LOGGER.warning(f"No grid parameter found for realization {realization}")
            return None
        if len(fn_list) > 1:
            raise ValueError(
                f"Multiple grid parameters found for: {realization}"
                "Something has gone terribly wrong."
            )
        grid_property = xtgeo.gridproperty_from_file(fn_list[0])
        fill_value = np.nan if not grid_property.isdiscrete else -1
        return grid_property.get_npvalues1d(order="F", fill_value=fill_value).ravel()

    def get_dynamic_property_values(
        self, property_name: str, property_date: str, realization: int
    ) -> Optional[np.ndarray]:
        fn_list: List[str] = self._locate_dynamic_property(
            property_name=property_name,
            property_datestr=property_date,
            realizations=[realization],
        )
        if len(fn_list) == 0:
            LOGGER.warning(f"No grid parameter found for realization {realization}")
            return None
        if len(fn_list) > 1:
            raise ValueError(
                f"Multiple grid parameters found for: {realization}"
                "Something has gone terribly wrong."
            )
        grid_property = xtgeo.gridproperty_from_file(fn_list[0])
        return grid_property.get_npvalues1d(order="F").ravel()

    def _locate_static_property(
        self, property_name: str, realizations: List[int]
    ) -> List[str]:
        """Returns list of file names matching the specified filter criteria"""
        df = self._inventory_df.loc[
            self._inventory_df[Col.TYPE] == GridType.STATIC_PROPERTY
        ]

        df = df.loc[
            (df[Col.ATTRIBUTE] == property_name) & (df[Col.REAL].isin(realizations))
        ]

        df = df[[Col.REL_PATH, Col.ORIGINAL_PATH]]

        # Return file name within backing store if the data was copied there,
        # otherwise return the original source file name
        fn_list: List[str] = []
        for _index, row in df.iterrows():
            if row[Col.REL_PATH]:
                fn_list.append(self._provider_dir / row[Col.REL_PATH])
            else:
                fn_list.append(row[Col.ORIGINAL_PATH])

        return fn_list

    def _locate_dynamic_property(
        self, property_name: str, property_datestr: str, realizations: List[int]
    ) -> List[str]:
        """Returns list of file names matching the specified filter criteria"""
        df = self._inventory_df.loc[
            self._inventory_df[Col.TYPE] == GridType.DYNAMIC_PROPERTY
        ]

        df = df.loc[
            (df[Col.ATTRIBUTE] == property_name)
            & (df[Col.DATESTR] == property_datestr)
            & (df[Col.REAL].isin(realizations))
        ]

        df = df[[Col.REL_PATH, Col.ORIGINAL_PATH]]

        # Return file name within backing store if the data was copied there,
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
        shutil.copyfile(src_path, provider_dir / dst_rel_path)

    # full_dst_path_arr = [storage_dir / dst_rel_path for dst_rel_path in store_path_arr]
    # with ProcessPoolExecutor() as executor:
    #     executor.map(shutil.copyfile, original_path_arr, full_dst_path_arr)


def _compose_rel_grid_pathstr(
    real: int,
    name: str,
    attribute: Optional[str],
    datestr: Optional[str],
    extension: str,
) -> str:
    """Compose path to grid file, relative to provider's directory"""
    if not attribute and not datestr:
        return str(Path(f"{real}--{name}{extension}"))
    if not datestr:
        return str(Path(f"{real}--{name}--{attribute}{extension}"))
    return str(Path(f"{real}--{name}--{attribute}--{datestr}{extension}"))
