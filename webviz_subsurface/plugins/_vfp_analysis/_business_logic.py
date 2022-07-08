import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from webviz_config import WebvizSettings
from webviz_config.webviz_store import webvizstore

from ._types import (
    AlqType,
    GfrType,
    PressureType,
    RateType,
    TabType,
    UnitSystem,
    WfrType,
)


class VfpTable:

    REQUIRED_COLUMNS = [
        "RATE",
        "PRESSURE",
        "WFR",
        "GFR",
        "ALQ",
        "TAB",
        "VFP_TYPE",
        "TABLE_NUMBER",
        "DATUM",
        "RATE_TYPE",
        "WFR_TYPE",
        "GFR_TYPE",
        "ALQ_TYPE",
        "PRESSURE_TYPE",
        "TAB_TYPE",
        "UNIT_TYPE",
    ]

    def __init__(self, table_nb: int, table_df: pd.DataFrame) -> None:

        self._table_nb = table_nb
        # This QCs that the required columns are there
        self._table_df = table_df[VfpTable.REQUIRED_COLUMNS]

        self._wfr_type = WfrType(self._get_parameter_type("WFR_TYPE"))
        self._gfr_type = GfrType(self._get_parameter_type("GFR_TYPE"))
        self._alq_type = AlqType(self._get_parameter_type("ALQ_TYPE"))
        self._pressure_type = PressureType(self._get_parameter_type("PRESSURE_TYPE"))
        self._rate_type = RateType(self._get_parameter_type("RATE_TYPE"))
        self._tab_type = TabType(self._get_parameter_type("TAB_TYPE"))
        self._unit_type = UnitSystem(self._get_parameter_type("UNIT_TYPE"))

    def get_parameter_data(self) -> Dict[str, Dict[str, Any]]:
        """Returns the VFP parameters"""
        return {
            "WFR": {
                "type": self._wfr_type,
                "values": sorted(list(self._table_df["WFR"].unique())),
            },
            "GFR": {
                "type": self._gfr_type,
                "values": sorted(list(self._table_df["GFR"].unique())),
            },
            "ALQ": {
                "type": self._alq_type,
                "values": sorted(list(self._table_df["ALQ"].unique())),
            },
            "PRESSURE": {
                "type": self._pressure_type,
                "values": sorted(list(self._table_df["PRESSURE"].unique())),
            },
            "RATE": {
                "type": self._rate_type,
                "values": sorted(list(self._table_df["RATE"].unique())),
            },
        }

    def _get_parameter_type(self, param_name: str) -> str:
        if self._table_df[param_name].nunique() > 1:
            raise ValueError(
                f"There can only be one {param_name} per table: "
                f"{self._table_df[param_name].unique()} was found "
                f"in table {self._table_nb}"
            )
        return self._table_df[param_name].values[0]


class VfpDataModel:
    """Class keeping the VFP data"""

    def __init__(
        self,
        webviz_settings: WebvizSettings,
        csvfile: str,
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
            self._csvfile = Path(ens_path) / csvfile
        else:
            self._csvfile = Path(csvfile)

        dframe = read_csv(self._csvfile)

        if dframe.empty:
            raise ValueError(f"No VFP tables found in file: {self._csvfile}")

        self._vfp_tables = {
            table_nb: VfpTable(table_nb, table_df)
            for table_nb, table_df in dframe.groupby("TABLE_NUMBER")
        }

    def get_vfp_numbers(self) -> List[int]:
        """Return unique vfp numbers"""
        return sorted(list(self._vfp_tables.keys()))

    def get_vfp_table(self, table_number: int) -> VfpTable:
        """Returns a VfpTable object corresponding to the given table number"""
        if not table_number in self._vfp_tables:
            raise ValueError(f"Vfp Table number {table_number} not found.")
        return self._vfp_tables[table_number]


@webvizstore
def read_csv(csv_file: str) -> pd.DataFrame:
    return pd.read_csv(csv_file)
