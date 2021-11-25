import fnmatch
import pathlib
import re
from typing import Callable, Dict, List, Optional, Tuple, Union

import pandas as pd
from fmu.ensemble import ScratchEnsemble
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore


class EnsembleModel:
    """Class to load data from a scratchensemble using fmu.ensemble"""

    def __init__(
        self,
        ensemble_name: str,
        ensemble_path: Union[str, pathlib.Path],
        filter_file: Union[str, None] = "OK",
    ) -> None:
        self.ensemble_name = ensemble_name
        self.ensemble_path = str(ensemble_path)
        self.filter_file = filter_file
        self._webviz_store: List = []

    def __repr__(self) -> str:
        return f"EnsembleModel: {self.ensemble_name, self.ensemble_path}"

    @property
    def ens_folder(self) -> dict:
        """Get root folder for ensemble"""
        return {
            self.ensemble_name: self.ensemble_path.split("realization", maxsplit=1)[0]
        }

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def load_ensemble(self) -> ScratchEnsemble:
        ensemble = (
            ScratchEnsemble(self.ensemble_name, self.ensemble_path)
            if self.filter_file is None
            else ScratchEnsemble(self.ensemble_name, self.ensemble_path).filter(
                self.filter_file
            )
        )
        if not ensemble.realizations:
            raise ValueError(
                f"No realizations found for ensemble {self.ensemble_name}, "
                f"located at '{self.ensemble_path}'. "
                "Aborting..."
            )
        return ensemble

    def load_parameters(self) -> pd.DataFrame:
        self._webviz_store.append(
            (
                self._load_parameters,
                [{"self": self}],
            )
        )
        return self._load_parameters()

    def load_smry(
        self,
        time_index: Optional[Union[list, str]] = None,
        column_keys: Optional[list] = None,
    ) -> pd.DataFrame:
        # Limit saved columns if time_index = 'raw' or None, as the data density might
        # be very high, and increases risk of `MemoryError`
        if time_index == "raw" or time_index is None:
            self._webviz_store.append(
                (
                    self._load_smry,
                    [
                        {
                            "self": self,
                            "time_index": time_index,
                            "column_keys": column_keys,
                        }
                    ],
                )
            )
            return self._load_smry(time_index=time_index, column_keys=column_keys)

        # Otherwise store all columns to reduce risk of duplicates
        self._webviz_store.append(
            (
                self._load_smry,
                [{"self": self, "time_index": time_index, "column_keys": None}],
            )
        )

        if column_keys is None:
            return self._load_smry(time_index=time_index)
        df = self._load_smry(time_index=time_index)
        return df[
            df.columns[_match_column_keys(df_index=df.columns, column_keys=column_keys)]
        ]

    def load_smry_meta(
        self,
        column_keys: Optional[list] = None,
    ) -> pd.DataFrame:
        """Finds metadata for the summary vectors in the ensemble."""
        self._webviz_store.append(
            (self._load_smry_meta, [{"self": self, "column_keys": None}])
        )
        if column_keys is None:
            return self._load_smry_meta()
        df = self._load_smry_meta()
        return df[_match_column_keys(df_index=df.index, column_keys=column_keys)]

    def load_csv(self, csv_file: pathlib.Path) -> pd.DataFrame:
        self._webviz_store.append(
            (
                self._load_csv,
                [{"self": self, "csv_file": csv_file}],
            )
        )
        return self._load_csv(csv_file=csv_file)

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    @webvizstore
    def _load_parameters(self) -> pd.DataFrame:
        return self.load_ensemble().parameters

    # What should we do with the memoize decorator here?
    # If we leave it in place, we will spend memory storing the pickled version of the
    # return value wich is a waste when we're running a portable app.
    # On the other hand, if we remove it we will save the memory, but during build of
    # a portable app we will end up loading the ensemble's smry data twice. Once during
    # normal init of the plugins and once when saving to the webviz store.
    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    @webvizstore
    def _load_smry(
        self,
        time_index: Optional[Union[list, str]] = None,
        column_keys: Optional[list] = None,
    ) -> pd.DataFrame:
        return self.load_ensemble().get_smry(
            time_index=time_index, column_keys=column_keys
        )

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    @webvizstore
    def _load_smry_meta(
        self,
        column_keys: Optional[list] = None,
    ) -> pd.DataFrame:
        """Finds metadata for the summary vectors in the ensemble."""
        return pd.DataFrame(
            self.load_ensemble().get_smry_meta(column_keys=column_keys)
        ).T

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    @webvizstore
    def _load_csv(self, csv_file: pathlib.Path) -> pd.DataFrame:
        return self.load_ensemble().load_csv(str(csv_file))

    @property
    def webviz_store(self) -> List[Tuple[Callable, List[Dict]]]:
        return self._webviz_store


def _match_column_keys(
    df_index: pd.core.indexes.base.Index, column_keys: List[str]
) -> pd.core.indexes.base.Index:
    """Matches patterns in column_keys with the columns in df_columns, and adds 'DATE' and
    'REAL' to the requested column patterns.
    """
    all_columns_keys = ["DATE", "REAL"]
    all_columns_keys.extend(column_keys)
    regex = re.compile(
        "|".join([fnmatch.translate(column_key) for column_key in all_columns_keys])
    )
    return df_index.map(lambda column: bool(regex.fullmatch(column)))
