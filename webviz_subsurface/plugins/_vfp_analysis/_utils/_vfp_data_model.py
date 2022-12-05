import glob
import io
import json
import logging
import re
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
    VFPPROD_UNITS,
    VFPTYPE,
    WFR,
)
from webviz_config import WebvizSettings
from webviz_config.webviz_store import webvizstore

from .._types import PressureType, VfpParam


class VfpTable:
    """Class that contains data and metadata for one VFP table"""

    def __init__(self, filename: str):
        self._filename = filename
        self._data = json.load(_read_vfp_arrow(self._filename))
        self._vfp_type = VFPTYPE(self._data["VFP_TYPE"])
        if self._vfp_type == VFPTYPE.VFPINJ:
            raise NotImplementedError(
                f"""
Could not load {self._filename}. VFPINJ tables not implemented.
            """
            )

        self._table_number = self._data["TABLE_NUMBER"]
        self._tab_type = VFPPROD_TABTYPE(self._data["TAB_TYPE"])
        self._unit_type = UNITTYPE(self._data["UNIT_TYPE"])
        self._datum = self._data["DATUM"]

        self.params = {
            VfpParam.THP: dict(enumerate(self._data["THP_VALUES"])),
            VfpParam.WFR: dict(enumerate(self._data["WFR_VALUES"])),
            VfpParam.GFR: dict(enumerate(self._data["GFR_VALUES"])),
            VfpParam.ALQ: dict(enumerate(self._data["ALQ_VALUES"])),
            VfpParam.RATE: dict(enumerate(self._data["FLOW_VALUES"])),
        }
        self.param_types = {
            VfpParam.THP: THPTYPE(self._data["THP_TYPE"]),
            VfpParam.WFR: WFR(self._data["WFR_TYPE"]),
            VfpParam.GFR: GFR(self._data["GFR_TYPE"]),
            VfpParam.ALQ: ALQ(self._data["ALQ_TYPE"]),
            VfpParam.RATE: VFPPROD_FLO(self._data["RATE_TYPE"]),
        }
        self._param_units = {
            VfpParam.THP: VFPPROD_UNITS[self._unit_type.value]["THP"][
                self.param_types[VfpParam.THP].value
            ],
            VfpParam.WFR: VFPPROD_UNITS[self._unit_type.value]["WFR"][
                self.param_types[VfpParam.WFR].value
            ],
            VfpParam.GFR: VFPPROD_UNITS[self._unit_type.value]["GFR"][
                self.param_types[VfpParam.GFR].value
            ],
            VfpParam.ALQ: VFPPROD_UNITS[self._unit_type.value]["ALQ"][
                self.param_types[VfpParam.ALQ].value
            ],
            VfpParam.RATE: VFPPROD_UNITS[self._unit_type.value]["FLO"][
                self.param_types[VfpParam.RATE].value
            ],
        }
        self._bhp_table = np.array(self._data["BHP_TABLE"])

        # pylint: disable=too-many-function-args
        self._reshaped_bhp_table = self._bhp_table.reshape(
            len(self.params[VfpParam.THP]),
            len(self.params[VfpParam.WFR]),
            len(self.params[VfpParam.GFR]),
            len(self.params[VfpParam.ALQ]),
            len(self.params[VfpParam.RATE]),
        )

    def get_rate_label(self) -> str:
        return f"""
{self.param_types[VfpParam.RATE].value.capitalize()} rate ({self._param_units[VfpParam.RATE]})
"""

    def get_bhp_label(self, pressure_type: PressureType) -> str:
        return f"{pressure_type.value} ({self._param_units[VfpParam.THP]})"

    def get_bhp_series(
        self,
        pressure_type: PressureType,
        thp_idx: int,
        wfr_idx: int,
        gfr_idx: int,
        alq_idx: int,
    ) -> List[float]:
        """Returns a series of bhp values for the given vfp parameter indices.
        The series has the same length as the rate values.

        If pressure_type is DP then the THP at the given thp index is subtracted
        from all the BHP values.
        """
        bhp_values = self._reshaped_bhp_table[thp_idx][wfr_idx][gfr_idx][alq_idx]
        if pressure_type == PressureType.BHP:
            return bhp_values
        if pressure_type == PressureType.DP:
            return bhp_values - self.params[VfpParam.THP][thp_idx]
        raise ValueError(f"PressureType {pressure_type} not implemented")

    def get_values(
        self, vfp_param: VfpParam, indices: Optional[List[int]] = None
    ) -> List[float]:
        """Returns the values for a given vfp param.

        If a list of indices is given, then only the values for those
        indices is returned.
        """
        if indices is None:
            return list(self.params[vfp_param].values())
        return [self.params[vfp_param][idx] for idx in indices]

    def get_metadata_markdown(self) -> str:
        """Returns a markdown with all the table metadata."""
        thp_values = ", ".join([str(val) for val in self.params[VfpParam.THP].values()])
        wfr_values = ", ".join([str(val) for val in self.params[VfpParam.WFR].values()])
        gfr_values = ", ".join([str(val) for val in self.params[VfpParam.GFR].values()])
        alq_values = ", ".join([str(val) for val in self.params[VfpParam.ALQ].values()])
        rate_values = ", ".join(
            [str(val) for val in self.params[VfpParam.RATE].values()]
        )
        return f"""
> - **VFP type**: {self._vfp_type.name}
> - **Table number**: {self._table_number}
> - **Units**: {self._unit_type.name}
> - **Datum**: {self._datum}
> - **THP type**: {self.param_types[VfpParam.THP].name} ({self._param_units[VfpParam.THP]})
> - **WFR type**: {self.param_types[VfpParam.WFR].name} ({self._param_units[VfpParam.WFR]})
> - **GFR type**: {self.param_types[VfpParam.GFR].name} ({self._param_units[VfpParam.GFR]})
> - **ALQ type**: {self.param_types[VfpParam.ALQ].name} ({self._param_units[VfpParam.ALQ]})
> - **Rate type**: {self.param_types[VfpParam.RATE].name} ({self._param_units[VfpParam.RATE]})
> - **THP values**: {thp_values}
> - **WFR values**: {wfr_values}
> - **GFR values**: {gfr_values}
> - **ALQ values**: {alq_values}
> - **Rate values**: {rate_values}
        """


class VfpDataModel:
    """Class for loading a keeping all the VFP tables."""

    def __init__(
        self,
        webviz_settings: WebvizSettings,
        vfp_file_pattern: str,
        ensemble: Optional[str] = None,
        realization: Optional[int] = None,
    ):
        if ensemble is not None:
            if isinstance(ensemble, list):
                raise TypeError(
                    'Incorrent argument type, "ensemble" must be a string instead of a list'
                )

            ens_path = webviz_settings.shared_settings["scratch_ensembles"][ensemble]

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

        self._vfp_files = json.load(_discover_files(self._vfp_file_pattern))
        if not self._vfp_files:
            raise FileNotFoundError(
                "No VFP arrow files found matching input file pattern."
            )

        self._vfp_tables = {}
        for table_name, file_name in self._vfp_files.items():
            try:
                self._vfp_tables[table_name] = VfpTable(file_name)
            except NotImplementedError as exc:
                logging.warning(exc)

    @property
    def webviz_store(self) -> List[Tuple[Callable, List[Dict]]]:
        return [(_discover_files, [{"file_pattern": self._vfp_file_pattern}]),] + [
            (_read_vfp_arrow, [{"filename": filename}])
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
    """Returns all the files that matches the input file pattern."""
    files = {
        file_name.split("/")[-1].replace(".arrow", ""): file_name
        for file_name in glob.glob(file_pattern)
    }
    return io.BytesIO(json.dumps(files).encode())


@webvizstore
def _read_vfp_arrow(filename: str) -> io.BytesIO:
    """Function to read the vfp arrow files and return them as
    a io.BytesIO object in order to be stored as portable.

    Uses the pyarrow2basic_data function from ecl2df in order
    to convert the pyarrow table into a dictionary. But then
    the columns have to be converted to strings, or lists in order
    to be encoded.
    """
    source = pa.memory_map(filename, "r")
    reader = pa.ipc.RecordBatchFileReader(source)
    pa_table = reader.read_all()
    vfp_dict = pyarrow2basic_data(pa_table)

    for key, _ in vfp_dict.items():
        # Convert types to strings
        if key.endswith("_TYPE"):
            vfp_dict[key] = str(vfp_dict[key].value)
        # Convert ndarrays to lists
        if (
            key.endswith("_VALUES")
            or key.endswith("_TABLE")
            or key.endswith("_INDICES")
        ):
            vfp_dict[key] = vfp_dict[key].tolist()

    return io.BytesIO(json.dumps(vfp_dict).encode())
