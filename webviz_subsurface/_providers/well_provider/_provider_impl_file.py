import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

import xtgeo

from webviz_subsurface._utils.perf_timer import PerfTimer

from .well_provider import WellPath, WellProvider

LOGGER = logging.getLogger(__name__)


INV_KEY_REL_PATH = "rel_path"
INV_KEY_MD_LOGNAME = "md_logname"


class ProviderImplFile(WellProvider):
    def __init__(
        self, provider_id: str, provider_dir: Path, inventory: Dict[str, dict]
    ) -> None:
        self._provider_id = provider_id
        self._provider_dir = provider_dir
        self._inventory = inventory

    @staticmethod
    def write_backing_store(
        storage_dir: Path,
        storage_key: str,
        well_file_names: List[str],
        md_logname: Optional[str],
    ) -> None:

        timer = PerfTimer()

        # All data for this provider will be stored inside a sub-directory
        # given by the storage key
        provider_dir = storage_dir / storage_key
        LOGGER.debug(f"Writing well backing store to: {provider_dir}")
        provider_dir.mkdir(parents=True, exist_ok=True)

        inventory_dict: Dict[str, dict] = {}

        LOGGER.debug(f"Writing {len(well_file_names)} wells into backing store...")

        timer.lap_s()
        for file_name in well_file_names:
            well = xtgeo.well_from_file(wfile=file_name, mdlogname=md_logname)

            if well.mdlogname is None:
                try:
                    well.geometrics()
                except ValueError:
                    LOGGER.debug(f"Ignoring {well.name} as MD cannot be calculated")
                    continue

            print("well.mdlogname=", well.mdlogname)

            well_name = well.name
            rel_path = f"{well_name}.rmswell"
            # rel_path = f"{well_name}.hdf"

            dst_file = provider_dir / rel_path
            print("dst_file=", dst_file)
            well.to_file(wfile=dst_file, fformat="rmswell")
            # well.to_hdf(wfile=dst_file)

            inventory_dict[well_name] = {
                INV_KEY_REL_PATH: rel_path,
                INV_KEY_MD_LOGNAME: well.mdlogname,
            }

        et_copy_s = timer.lap_s()

        json_fn = provider_dir / "inventory.json"
        with open(json_fn, "w") as file:
            json.dump(inventory_dict, file)

        LOGGER.debug(
            f"Wrote well backing store in: {timer.elapsed_s():.2f}s ("
            f"copy={et_copy_s:.2f}s)"
        )

    @staticmethod
    def from_backing_store(
        storage_dir: Path,
        storage_key: str,
    ) -> Optional["ProviderImplFile"]:

        provider_dir = storage_dir / storage_key
        json_fn = provider_dir / "inventory.json"

        try:
            with open(json_fn, "r") as file:
                inventory = json.load(file)
        except FileNotFoundError:
            return None

        return ProviderImplFile(storage_key, provider_dir, inventory)

    def provider_id(self) -> str:
        return self._provider_id

    def well_names(self) -> List[str]:
        return sorted(list(self._inventory.keys()))

    def get_well_path(self, well_name: str) -> WellPath:
        well = self.get_well_xtgeo_obj(well_name)
        df = well.dataframe
        md_logname = well.mdlogname

        x_arr = df["X_UTME"].to_numpy()
        y_arr = df["Y_UTMN"].to_numpy()
        z_arr = df["Z_TVDSS"].to_numpy()
        md_arr = df[md_logname].to_numpy()

        return WellPath(x_arr=x_arr, y_arr=y_arr, z_arr=z_arr, md_arr=md_arr)

    def get_well_xtgeo_obj(self, well_name: str) -> xtgeo.Well:
        well_entry = self._inventory.get(well_name)
        if not well_entry:
            raise ValueError(f"Requested well name {well_name} not found")

        rel_fn = well_entry[INV_KEY_REL_PATH]
        md_logname = well_entry[INV_KEY_MD_LOGNAME]

        full_file_name = self._provider_dir / rel_fn
        well = xtgeo.well_from_file(
            wfile=full_file_name, fformat="rmswell", mdlogname=md_logname
        )

        return well
