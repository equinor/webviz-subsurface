import glob
import io
import json
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pyarrow as pa
from ecl2df.vfp import pyarrow2basic_data
from ecl2df.vfp._vfpdefs import (
    ALQ,
    GFR,
    THPTYPE,
    UNITTYPE,
    VFPPROD_FLO,
    VFPPROD_TABTYPE,
    VFPTYPE,
    WFR,
)
from webviz_config import WebvizSettings
from webviz_config.webviz_store import webvizstore

from .._types import PressureType, VfpParam


class VfpTable:
    """Descr"""

    def __init__(self, filename: str):
        self._filename = filename
        self._data = json.load(_read_arrow_file(self._filename))
        self.vfp_type = VFPTYPE(self._data["VFP_TYPE"])
        self.tab_type = VFPPROD_TABTYPE(self._data["TAB_TYPE"])
        self.rate_type = VFPPROD_FLO(self._data["RATE_TYPE"])
        self.unit_type = UNITTYPE(self._data["UNIT_TYPE"])
        self.rate_values = self._data["FLOW_VALUES"]

        self.params = {
            VfpParam.THP: dict(enumerate(self._data["THP_VALUES"])),
            VfpParam.WFR: dict(enumerate(self._data["WFR_VALUES"])),
            VfpParam.GFR: dict(enumerate(self._data["GFR_VALUES"])),
            VfpParam.ALQ: dict(enumerate(self._data["ALQ_VALUES"])),
        }
        self.param_types = {
            VfpParam.THP: THPTYPE(self._data["THP_TYPE"]),
            VfpParam.WFR: WFR(self._data["WFR_TYPE"]),
            VfpParam.GFR: GFR(self._data["GFR_TYPE"]),
            VfpParam.ALQ: ALQ(self._data["ALQ_TYPE"]),
        }
        self._bhp_table = np.array(self._data["BHP_TABLE"])

        # pylint: disable=too-many-function-args
        self._reshaped_bhp_table = self._bhp_table.reshape(
            len(self.params[VfpParam.THP]),
            len(self.params[VfpParam.WFR]),
            len(self.params[VfpParam.GFR]),
            len(self.params[VfpParam.ALQ]),
            len(self.rate_values),
        )

    def get_bhp_series(
        self,
        pressure_type: PressureType,
        thp_idx: int,
        wfr_idx: int,
        gfr_idx: int,
        alq_idx: int,
    ) -> List[float]:
        """Descr"""
        bhp_values = self._reshaped_bhp_table[thp_idx][wfr_idx][gfr_idx][alq_idx]
        if pressure_type == PressureType.BHP:
            return bhp_values
        if pressure_type == PressureType.DP:
            return bhp_values - self.params[VfpParam.THP][thp_idx]
        raise ValueError(f"PressureType {pressure_type} not implemented")

    def get_values(
        self, param_type: VfpParam, indices: Optional[List[int]]
    ) -> List[float]:
        """Descr"""
        if indices is None:
            return list(self.params[param_type].values())
        return [self.params[param_type][idx] for idx in indices]


class VfpDataModel:
    """Class keeping the VFP data"""

    def __init__(
        self,
        webviz_settings: WebvizSettings,
        vfp_file_pattern: str,
        ensemble: Optional[str] = None,
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

        self._vfp_files = json.load(_discover_files(self._vfp_file_pattern))
        self._vfp_tables = {
            table_name: VfpTable(file_name)
            for table_name, file_name in self._vfp_files.items()
        }

    @property
    def webviz_store(self) -> List[Tuple[Callable, List[Dict]]]:
        return [(_discover_files, [{"file_pattern": self._vfp_file_pattern}]),] + [
            (_read_arrow_file, [{"filename": filename}])
            for filename in self._vfp_files.values()
        ]

    @property
    def vfp_names(self) -> List[str]:
        """Return unique vfp names"""
        return list(self._vfp_tables.keys())

    def get_vfp_table(self, vfp_name: str) -> VfpTable:
        """Returns a VfpTable object corresponding to the given table number"""
        if not vfp_name in self._vfp_tables:
            raise ValueError(f"Vfp Table: {vfp_name} not found.")
        return self._vfp_tables[vfp_name]


@webvizstore
def _discover_files(file_pattern: str) -> io.BytesIO:
    """Descr"""
    files = {
        file_name.split("/")[-1].replace(".arrow", ""): file_name
        for file_name in glob.glob(file_pattern)
    }
    return io.BytesIO(json.dumps(files).encode())


@webvizstore
def _read_arrow_file(filename: str) -> io.BytesIO:
    source = pa.memory_map(filename, "r")
    reader = pa.ipc.RecordBatchFileReader(source)
    pa_table = reader.read_all()
    vfp_dict = pyarrow2basic_data(pa_table)

    for column in [
        "VFP_TYPE",
        "RATE_TYPE",
        "WFR_TYPE",
        "GFR_TYPE",
        "ALQ_TYPE",
        "THP_TYPE",
        "UNIT_TYPE",
        "TAB_TYPE",
    ]:
        vfp_dict[column] = str(vfp_dict[column].value)

    for column in [
        "THP_VALUES",
        "WFR_VALUES",
        "GFR_VALUES",
        "ALQ_VALUES",
        "FLOW_VALUES",
        "BHP_TABLE",
        "THP_INDICES",
        "WFR_INDICES",
        "GFR_INDICES",
        "ALQ_INDICES",
    ]:
        vfp_dict[column] = vfp_dict[column].tolist()

    return io.BytesIO(json.dumps(vfp_dict).encode())
