import glob
import re
from typing import Any, Dict, List, Optional

import pyarrow as pa
from ecl2df.vfp import pyarrow2basic_data
from webviz_config import WebvizSettings
from webviz_config.webviz_store import webvizstore


class VfpTable:
    """Descr"""

    def __init__(self, filename: str):
        self._filename = filename
        self._data = self._read_file()
        self.vfp_type = self._data["VFP_TYPE"]
        self.tab_type = self._data["TAB_TYPE"]
        self.rate_values = self._data["FLOW_VALUES"]
        self.thp_dict = dict(enumerate(self._data["THP_VALUES"]))
        self.wfr_dict = dict(enumerate(self._data["WFR_VALUES"]))
        self.gfr_dict = dict(enumerate(self._data["GFR_VALUES"]))
        self.alq_dict = dict(enumerate(self._data["ALQ_VALUES"]))
        self.rate_type = self._data["RATE_TYPE"]
        self.thp_type = self._data["THP_TYPE"]
        self.wfr_type = self._data["WFR_TYPE"]
        self.gfr_type = self._data["GFR_TYPE"]
        self.alq_type = self._data["ALQ_TYPE"]

        self._reshaped_bhp_table = self._data["BHP_TABLE"].reshape(
            len(self.thp_dict),
            len(self.wfr_dict),
            len(self.gfr_dict),
            len(self.alq_dict),
            len(self.rate_values),
        )

    def get_bhp_series(
        self, thp_idx: int, wfr_idx: int, gfr_idx: int, alq_idx: int
    ) -> List[float]:
        """Descr"""
        return self._reshaped_bhp_table[thp_idx][wfr_idx][gfr_idx][alq_idx]

    def _read_file(self) -> Dict[str, Any]:
        source = pa.memory_map(self._filename, "r")
        reader = pa.ipc.RecordBatchFileReader(source)
        pa_table = reader.read_all()
        return pyarrow2basic_data(pa_table)


class VfpDataModel:
    """Class keeping the VFP data"""

    def __init__(
        self,
        webviz_settings: WebvizSettings,
        vfp_file_pattern: str,
        ensemble: str = None,
        realization: Optional[int] = None,
    ):

        if ensemble is not None:
            if isinstance(ensemble, list):
                raise TypeError(
                    'Incorrent argument type, "ensemble" must be a string instead of a list'
                )
            if realization is None:
                raise ValueError('Incorrent arguments, "realization" must be specified')

            ens_path = webviz_settings.shared_settings["scratch_ensembles"][ensemble]
            # replace realization in string from scratch_ensemble with input realization
            ens_path = re.sub(
                "realization-[^/]", f"realization-{realization}", ens_path
            )
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
