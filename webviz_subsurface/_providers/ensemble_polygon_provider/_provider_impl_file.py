import logging
import shutil
from pathlib import Path
from typing import List, Optional

import pandas as pd
import xtgeo

from webviz_subsurface._utils.enum_shim import StrEnum
from webviz_subsurface._utils.perf_timer import PerfTimer

from ._polygon_discovery import PolygonsFileInfo
from .ensemble_polygon_provider import (
    EnsemblePolygonProvider,
    PolygonsAddress,
    SimulatedPolygonsAddress,
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


class PolygonType(StrEnum):
    SIMULATED = "simulated"
    HAZARDUOUS_BOUNDARY = "hazarduous_boundary"
    CONTAINMENT_BOUNDARY = "containment_boundary"


class ProviderImplFile(EnsemblePolygonProvider):
    def __init__(
        self,
        provider_id: str,
        provider_dir: Path,
        polygon_inventory_df: pd.DataFrame,
    ) -> None:
        self._provider_id = provider_id
        self._provider_dir = provider_dir
        self._inventory_df = polygon_inventory_df

    @staticmethod
    # pylint: disable=too-many-locals
    def write_backing_store(
        storage_dir: Path,
        storage_key: str,
        sim_polygons: List[PolygonsFileInfo],
    ) -> None:
        timer = PerfTimer()

        # All data for this provider will be stored inside a sub-directory
        # given by the storage key
        provider_dir = storage_dir / storage_key
        LOGGER.debug(f"Writing polygon backing store to: {provider_dir}")
        provider_dir.mkdir(parents=True, exist_ok=True)
        (provider_dir / REL_SIM_DIR).mkdir(parents=True, exist_ok=True)

        type_arr: List[PolygonType] = []
        real_arr: List[int] = []
        attribute_arr: List[str] = []
        name_arr: List[str] = []
        rel_path_arr: List[str] = []
        original_path_arr: List[str] = []

        for polygon_info in sim_polygons:
            rel_path_in_store = _compose_rel_sim_polygons_path(
                real=polygon_info.real,
                attribute=polygon_info.attribute,
                name=polygon_info.name,
                extension=Path(polygon_info.path).suffix,
            )
            type_arr.append(PolygonType.SIMULATED)
            real_arr.append(polygon_info.real)
            attribute_arr.append(polygon_info.attribute)
            name_arr.append(polygon_info.name)
            rel_path_arr.append(str(rel_path_in_store))
            original_path_arr.append(polygon_info.path)

        LOGGER.debug(f"Copying {len(original_path_arr)} polygons into backing store...")
        timer.lap_s()
        _copy_polygons_into_provider_dir(original_path_arr, rel_path_arr, provider_dir)
        et_copy_s = timer.lap_s()

        polygons_inventory_df = pd.DataFrame(
            {
                Col.TYPE: type_arr,
                Col.REAL: real_arr,
                Col.ATTRIBUTE: attribute_arr,
                Col.NAME: name_arr,
                Col.REL_PATH: rel_path_arr,
                Col.ORIGINAL_PATH: original_path_arr,
            }
        )

        parquet_file_name = provider_dir / "polygons_inventory.parquet"
        polygons_inventory_df.to_parquet(path=parquet_file_name)

        LOGGER.debug(
            f"Wrote polygon backing store in: {timer.elapsed_s():.2f}s ("
            f"copy={et_copy_s:.2f}s)"
        )

    @staticmethod
    def from_backing_store(
        storage_dir: Path,
        storage_key: str,
    ) -> Optional["ProviderImplFile"]:
        provider_dir = storage_dir / storage_key
        parquet_file_name = provider_dir / "polygons_inventory.parquet"

        try:
            polygons_inventory_df = pd.read_parquet(path=parquet_file_name)
            return ProviderImplFile(storage_key, provider_dir, polygons_inventory_df)
        except FileNotFoundError:
            return None

    def provider_id(self) -> str:
        return self._provider_id

    def attributes(self) -> List[str]:
        return sorted(list(self._inventory_df[Col.ATTRIBUTE].unique()))

    def fault_polygons_names_for_attribute(self, polygons_attribute: str) -> List[str]:
        return sorted(
            list(
                self._inventory_df.loc[
                    self._inventory_df[Col.ATTRIBUTE] == polygons_attribute
                ][Col.NAME].unique()
            )
        )

    def realizations(self) -> List[int]:
        unique_reals = self._inventory_df[Col.REAL].unique()

        # Sort and strip out any entries with real == -1
        return sorted([r for r in unique_reals if r >= 0])

    def get_polygons(
        self,
        address: PolygonsAddress,
    ) -> Optional[xtgeo.Polygons]:
        if isinstance(address, SimulatedPolygonsAddress):
            return self._get_simulated_polygons(address)

        raise TypeError("Unknown type of fault polygons address")

    def _get_simulated_polygons(
        self, address: SimulatedPolygonsAddress
    ) -> Optional[xtgeo.Polygons]:
        """Returns a Xtgeo fault polygons instance of a single realization fault polygons"""

        timer = PerfTimer()

        polygons_fns: List[Path] = self._locate_simulated_polygons(
            attribute=address.attribute,
            name=address.name,
            realizations=[address.realization],
        )

        if len(polygons_fns) == 0:
            LOGGER.warning(f"No simulated polygons found for {address}")
            return None
        if len(polygons_fns) > 1:
            LOGGER.warning(
                f"Multiple simulated polygonss found for: {address}"
                "Returning first fault polygons."
            )

        if polygons_fns[0].suffix == ".csv":
            polygons = xtgeo.Polygons(pd.read_csv(polygons_fns[0]))
        else:
            polygons = xtgeo.polygons_from_file(polygons_fns[0])

        LOGGER.debug(f"Loaded simulated fault polygons in: {timer.elapsed_s():.2f}s")

        return polygons

    def _locate_simulated_polygons(
        self, attribute: str, name: str, realizations: List[int]
    ) -> List[Path]:
        """Returns list of file names matching the specified filter criteria"""
        df = self._inventory_df.loc[
            self._inventory_df[Col.TYPE] == PolygonType.SIMULATED
        ]

        df = df.loc[
            (df[Col.ATTRIBUTE] == attribute)
            & (df[Col.NAME] == name)
            & (df[Col.REAL].isin(realizations))
        ]

        return [self._provider_dir / rel_path for rel_path in df[Col.REL_PATH]]


def _copy_polygons_into_provider_dir(
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


def _compose_rel_sim_polygons_path(
    real: int,
    attribute: str,
    name: str,
    extension: str,
) -> Path:
    """Compose path to simulated fault polygons file, relative to provider's directory"""
    fname = f"{real}--{name}--{attribute}{extension}"
    return Path(REL_SIM_DIR) / fname
