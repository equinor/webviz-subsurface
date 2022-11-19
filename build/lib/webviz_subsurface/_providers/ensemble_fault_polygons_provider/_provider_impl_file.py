import logging
import shutil
from enum import Enum
from pathlib import Path
from typing import List, Optional

import pandas as pd
import xtgeo

from webviz_subsurface._utils.perf_timer import PerfTimer

from ._fault_polygons_discovery import FaultPolygonsFileInfo
from .ensemble_fault_polygons_provider import (
    EnsembleFaultPolygonsProvider,
    FaultPolygonsAddress,
    SimulatedFaultPolygonsAddress,
)

LOGGER = logging.getLogger(__name__)

REL_SIM_DIR = "sim"


# pylint: disable=too-few-public-methods
class Col:
    TYPE = "type"
    REAL = "real"
    ATTRIBUTE = "attribute"
    NAME = "name"
    ORIGINAL_PATH = "original_path"
    REL_PATH = "rel_path"


class FaultPolygonsType(str, Enum):
    SIMULATED = "simulated"


class ProviderImplFile(EnsembleFaultPolygonsProvider):
    def __init__(
        self,
        provider_id: str,
        provider_dir: Path,
        fault_polygons_inventory_df: pd.DataFrame,
    ) -> None:
        self._provider_id = provider_id
        self._provider_dir = provider_dir
        self._inventory_df = fault_polygons_inventory_df

    @staticmethod
    # pylint: disable=too-many-locals
    def write_backing_store(
        storage_dir: Path,
        storage_key: str,
        sim_fault_polygons: List[FaultPolygonsFileInfo],
    ) -> None:

        timer = PerfTimer()

        # All data for this provider will be stored inside a sub-directory
        # given by the storage key
        provider_dir = storage_dir / storage_key
        LOGGER.debug(f"Writing fault polygons backing store to: {provider_dir}")
        provider_dir.mkdir(parents=True, exist_ok=True)
        (provider_dir / REL_SIM_DIR).mkdir(parents=True, exist_ok=True)

        type_arr: List[FaultPolygonsType] = []
        real_arr: List[int] = []
        attribute_arr: List[str] = []
        name_arr: List[str] = []
        rel_path_arr: List[str] = []
        original_path_arr: List[str] = []

        for fault_polygons_info in sim_fault_polygons:
            rel_path_in_store = _compose_rel_sim_fault_polygons_path(
                real=fault_polygons_info.real,
                attribute=fault_polygons_info.attribute,
                name=fault_polygons_info.name,
                extension=Path(fault_polygons_info.path).suffix,
            )
            type_arr.append(FaultPolygonsType.SIMULATED)
            real_arr.append(fault_polygons_info.real)
            attribute_arr.append(fault_polygons_info.attribute)
            name_arr.append(fault_polygons_info.name)
            rel_path_arr.append(str(rel_path_in_store))
            original_path_arr.append(fault_polygons_info.path)

        LOGGER.debug(
            f"Copying {len(original_path_arr)} fault polygons into backing store..."
        )
        timer.lap_s()
        _copy_fault_polygons_into_provider_dir(
            original_path_arr, rel_path_arr, provider_dir
        )
        et_copy_s = timer.lap_s()

        fault_polygons_inventory_df = pd.DataFrame(
            {
                Col.TYPE: type_arr,
                Col.REAL: real_arr,
                Col.ATTRIBUTE: attribute_arr,
                Col.NAME: name_arr,
                Col.REL_PATH: rel_path_arr,
                Col.ORIGINAL_PATH: original_path_arr,
            }
        )

        parquet_file_name = provider_dir / "fault_polygons_inventory.parquet"
        fault_polygons_inventory_df.to_parquet(path=parquet_file_name)

        LOGGER.debug(
            f"Wrote fault polygons backing store in: {timer.elapsed_s():.2f}s ("
            f"copy={et_copy_s:.2f}s)"
        )

    @staticmethod
    def from_backing_store(
        storage_dir: Path,
        storage_key: str,
    ) -> Optional["ProviderImplFile"]:

        provider_dir = storage_dir / storage_key
        parquet_file_name = provider_dir / "fault_polygons_inventory.parquet"

        try:
            fault_polygons_inventory_df = pd.read_parquet(path=parquet_file_name)
            return ProviderImplFile(
                storage_key, provider_dir, fault_polygons_inventory_df
            )
        except FileNotFoundError:
            return None

    def provider_id(self) -> str:
        return self._provider_id

    def attributes(self) -> List[str]:
        return sorted(list(self._inventory_df[Col.ATTRIBUTE].unique()))

    def fault_polygons_names_for_attribute(
        self, fault_polygons_attribute: str
    ) -> List[str]:
        return sorted(
            list(
                self._inventory_df.loc[
                    self._inventory_df[Col.ATTRIBUTE] == fault_polygons_attribute
                ][Col.NAME].unique()
            )
        )

    def realizations(self) -> List[int]:
        unique_reals = self._inventory_df[Col.REAL].unique()

        # Sort and strip out any entries with real == -1
        return sorted([r for r in unique_reals if r >= 0])

    def get_fault_polygons(
        self,
        address: FaultPolygonsAddress,
    ) -> Optional[xtgeo.Polygons]:

        if isinstance(address, SimulatedFaultPolygonsAddress):
            return self._get_simulated_fault_polygons(address)

        raise TypeError("Unknown type of fault polygons address")

    def _get_simulated_fault_polygons(
        self, address: SimulatedFaultPolygonsAddress
    ) -> Optional[xtgeo.Polygons]:
        """Returns a Xtgeo fault polygons instance of a single realization fault polygons"""

        timer = PerfTimer()

        fault_polygons_fns: List[str] = self._locate_simulated_fault_polygons(
            attribute=address.attribute,
            name=address.name,
            realizations=[address.realization],
        )

        if len(fault_polygons_fns) == 0:
            LOGGER.warning(f"No simulated fault polygons found for {address}")
            return None
        if len(fault_polygons_fns) > 1:
            LOGGER.warning(
                f"Multiple simulated fault polygonss found for: {address}"
                "Returning first fault polygons."
            )

        fault_polygons = xtgeo.polygons_from_file(fault_polygons_fns[0])

        LOGGER.debug(f"Loaded simulated fault polygons in: {timer.elapsed_s():.2f}s")

        return fault_polygons

    def _locate_simulated_fault_polygons(
        self, attribute: str, name: str, realizations: List[int]
    ) -> List[str]:
        """Returns list of file names matching the specified filter criteria"""
        df = self._inventory_df.loc[
            self._inventory_df[Col.TYPE] == FaultPolygonsType.SIMULATED
        ]

        df = df.loc[
            (df[Col.ATTRIBUTE] == attribute)
            & (df[Col.NAME] == name)
            & (df[Col.REAL].isin(realizations))
        ]

        return [self._provider_dir / rel_path for rel_path in df[Col.REL_PATH]]


def _copy_fault_polygons_into_provider_dir(
    original_path_arr: List[str],
    rel_path_arr: List[str],
    provider_dir: Path,
) -> None:
    for src_path, dst_rel_path in zip(original_path_arr, rel_path_arr):
        # LOGGER.debug(f"copying fault polygons from: {src_path}")
        shutil.copyfile(src_path, provider_dir / dst_rel_path)

    # full_dst_path_arr = [storage_dir / dst_rel_path for dst_rel_path in store_path_arr]
    # with ProcessPoolExecutor() as executor:
    #     executor.map(shutil.copyfile, original_path_arr, full_dst_path_arr)


def _compose_rel_sim_fault_polygons_path(
    real: int,
    attribute: str,
    name: str,
    extension: str,
) -> Path:
    """Compose path to simulated fault polygons file, relative to provider's directory"""
    fname = f"{real}--{name}--{attribute}{extension}"
    return Path(REL_SIM_DIR) / fname
