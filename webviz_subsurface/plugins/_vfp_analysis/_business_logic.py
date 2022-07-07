import re
from pathlib import Path
from typing import List, Optional

import pandas as pd
from webviz_config import WebvizSettings
from webviz_config.webviz_store import webvizstore


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

        self._dframe = read_csv(self._csvfile)

        ## QC that the right columns are there

    def get_vfp_numbers(self) -> List[int]:
        """Return unique vfp numbers"""
        return sorted(list(self._dframe["TABLE_NUMBER"].unique()))


@webvizstore
def read_csv(csv_file: str) -> pd.DataFrame:
    return pd.read_csv(csv_file)
