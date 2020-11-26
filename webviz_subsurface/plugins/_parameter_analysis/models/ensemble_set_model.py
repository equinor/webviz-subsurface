from typing import Union, Optional, List
import pathlib

import pandas as pd
from fmu.ensemble import ScratchEnsemble, EnsembleSet
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore


class EnsembleSetModel:
    """Class to load and manipulate ensemble sets from scratch disk
    using fmu.ensemble"""

    def __init__(
        self,
        ensemble_paths: dict,
        ensemble_set_name: str = "EnsembleSet",
        filter_file: Union[str, None] = "OK",
    ) -> None:
        self.ensemble_paths = ensemble_paths
        self.ensemble_set_name = ensemble_set_name
        self.filter_file = filter_file
        self.webvizstore: List = []

    def __repr__(self) -> str:
        return f"EnsembleSetModel: {self.ensemble_paths}"

    @property
    def ens_folders(self):
        """Get root folders for ensemble set"""
        return {
            ens: pathlib.Path(ens_path.split("realization")[0])
            for ens, ens_path in self.ensemble_paths.items()
        }

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def load_ensemble_set(self) -> EnsembleSet:
        return EnsembleSet(
            self.ensemble_set_name,
            [
                ScratchEnsemble(ens_name, ens_path)
                if self.filter_file is None
                else ScratchEnsemble(ens_name, ens_path).filter(self.filter_file)
                for ens_name, ens_path in self.ensemble_paths.items()
            ],
        )

    def load_parameters(self):
        self.webvizstore.append(
            (
                self._load_parameters,
                [{"self": self}],
            )
        )
        return self._load_parameters()

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    @webvizstore
    def _load_parameters(self) -> pd.DataFrame:
        return self.load_ensemble_set().parameters

    def load_smry(
        self,
        time_index: Optional[Union[list, str]] = None,
        column_keys: Optional[list] = None,
    ) -> pd.DataFrame:
        self.webvizstore.append(
            (
                self._load_smry,
                [{"self": self, "time_index": time_index, "column_keys": column_keys}],
            )
        )
        return self._load_smry(time_index=time_index, column_keys=column_keys)

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    @webvizstore
    def _load_smry(
        self,
        time_index: Optional[Union[list, str]] = None,
        column_keys: Optional[list] = None,
    ) -> pd.DataFrame:

        return self.load_ensemble_set().get_smry(
            time_index=time_index, column_keys=column_keys
        )

    def load_smry_meta(
        self,
        column_keys: Optional[list] = None,
    ) -> pd.DataFrame:
        """Finds metadata for the summary vectors in the ensemble set.
        Note that we assume the same units for all ensembles.
        (meaning that we update/overwrite when checking the next ensemble)
        """
        self.webvizstore.append(
            (self._load_smry_meta, [{"self": self, "column_keys": column_keys}])
        )
        return self._load_smry_meta(column_keys=column_keys)

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    @webvizstore
    def _load_smry_meta(
        self,
        column_keys: Optional[list] = None,
    ) -> pd.DataFrame:
        """Finds metadata for the summary vectors in the ensemble set.
        Note that we assume the same units for all ensembles.
        (meaning that we update/overwrite when checking the next ensemble)
        """
        ensemble_set = self.load_ensemble_set()
        smry_meta = {}
        for ensname in ensemble_set.ensemblenames:
            smry_meta.update(
                ensemble_set[ensname].get_smry_meta(column_keys=column_keys)
            )
        return pd.DataFrame(smry_meta).transpose()

    def load_csv(self, csv_file: pathlib.Path) -> pd.DataFrame:
        self.webvizstore.append(
            (
                self._load_csv,
                [{"self": self, "csv_file": csv_file}],
            )
        )
        return self._load_csv(csv_file=csv_file)

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    @webvizstore
    def _load_csv(self, csv_file: pathlib.Path) -> pd.DataFrame:
        return self.load_ensemble_set().load_csv(str(csv_file))
