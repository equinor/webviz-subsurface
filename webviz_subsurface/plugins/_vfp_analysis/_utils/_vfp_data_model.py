import re
from pathlib import Path
from typing import Optional

from webviz_config import WebvizSettings
from webviz_config.webviz_store import webvizstore


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
            self._vfp_file_pattern = Path(ens_path) / vfp_file_pattern
        else:
            self._vfp_file_pattern = Path(vfp_file_pattern)

        # dframe = read_csv(self._csvfile)

        # if dframe.empty:
        #     raise ValueError(f"No VFP tables found in file: {self._csvfile}")

        # self._vfp_tables = {
        #     table_nb: VfpTable(table_nb, table_df)
        #     for table_nb, table_df in dframe.groupby("TABLE_NUMBER")
        # }


#     def get_vfp_numbers(self) -> List[int]:
#         """Return unique vfp numbers"""
#         return sorted(list(self._vfp_tables.keys()))

#     def get_vfp_table(self, table_number: int) -> VfpTable:
#         """Returns a VfpTable object corresponding to the given table number"""
#         if not table_number in self._vfp_tables:
#             raise ValueError(f"Vfp Table number {table_number} not found.")
#         return self._vfp_tables[table_number]


# @webvizstore
# def read_csv(csv_file: str) -> pd.DataFrame:
#     return pd.read_csv(csv_file)
