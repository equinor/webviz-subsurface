import glob
from typing import List

from webviz_config import WebvizSettings
from webviz_config.webviz_store import webvizstore

from ._vfp_table import VfpTable


class VfpDataModel:
    """Class keeping the VFP data"""

    def __init__(
        self,
        webviz_settings: WebvizSettings,
        vfp_file_pattern: str,
        ensemble: str = None,
    ):

        if ensemble is not None:
            if isinstance(ensemble, list):
                raise TypeError(
                    'Incorrent argument type, "ensemble" must be a string instead of a list'
                )

            ens_path = webviz_settings.shared_settings["scratch_ensembles"][ensemble]

            # Remove realization-* and iter_dir
            folders = []
            for folder in ens_path.split("/"):
                if folder.startswith("realization-"):
                    break
                folders.append(folder)

            ens_path = "/".join(folders)
            self._vfp_file_pattern = f"{ens_path}/{vfp_file_pattern}"
        else:
            self._vfp_file_pattern = vfp_file_pattern

        self._vfp_tables = {
            filename.split("/")[-1].replace(".arrow", ""): VfpTable(filename)
            for filename in glob.glob(self._vfp_file_pattern)
        }

    @property
    def vfp_names(self) -> List[str]:
        """Return unique vfp names"""
        return list(self._vfp_tables.keys())

    def get_vfp_table(self, vfp_name: str) -> VfpTable:
        """Returns a VfpTable object corresponding to the given table number"""
        if not vfp_name in self._vfp_tables:
            raise ValueError(f"Vfp Table: {vfp_name} not found.")
        return self._vfp_tables[vfp_name]
