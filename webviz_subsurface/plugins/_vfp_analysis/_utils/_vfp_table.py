from typing import Any, Dict, List

import pyarrow as pa
from ecl2df.vfp import pyarrow2basic_data


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
