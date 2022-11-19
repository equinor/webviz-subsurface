import pathlib
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import pandas as pd

from .ensemble_model import EnsembleModel


class EnsembleSetModel:
    """Class to load and manipulate ensemble sets from given paths to
    ensembles on disk"""

    def __init__(
        self,
        ensemble_paths: dict,
        smry_time_index: Optional[Union[list, str]] = None,
        smry_column_keys: Optional[list] = None,
    ) -> None:
        self._ensemble_paths = ensemble_paths
        self._webvizstore: List = []
        self._ensembles = [
            EnsembleModel(ens_name, ens_path, filter_file="OK")
            for ens_name, ens_path in self._ensemble_paths.items()
        ]

        self._smry_time_index = smry_time_index
        self._smry_column_keys = smry_column_keys
        self._cached_smry_df: Optional[pd.DataFrame] = None
        self._hash_for_cached_smry_df: Optional[pd.Series] = None

    def __repr__(self) -> str:
        return f"EnsembleSetModel: {self._ensemble_paths}"

    @property
    def ens_folders(self) -> dict:
        """Get root folders for ensemble set"""
        return {
            ens: pathlib.Path(ens_path.split("realization")[0])
            for ens, ens_path in self._ensemble_paths.items()
        }

    @staticmethod
    def _get_ensembles_data(
        ensemble_models: List[EnsembleModel], func: str, **kwargs: Any
    ) -> pd.DataFrame:
        """Runs the provided function for each ensemble and concats dataframes"""
        dfs = []
        for ensemble in ensemble_models:
            try:
                dframe = getattr(ensemble, func)(**kwargs)
                dframe.insert(0, "ENSEMBLE", ensemble.ensemble_name)
                dfs.append(dframe)
            except (KeyError, ValueError):
                # Happens if an ensemble is missing some data
                # Warning has already been issued at initialization
                pass
        if dfs:
            return pd.concat(dfs, sort=False)
        raise KeyError(f"No data found for {func} with arguments: {kwargs}")

    def load_parameters(self) -> pd.DataFrame:
        return EnsembleSetModel._get_ensembles_data(self._ensembles, "load_parameters")

    def get_or_load_smry_cached(self) -> pd.DataFrame:
        """Either loads smry data from file or retrieves a cached copy of DataFrame.
        Note that it is imperative that the returned DataFrame be treated as read-only
        since it will probably be shared by multiple clients.
        """

        if self._cached_smry_df is not None:
            # If we're returning cached data frame, try and verify that it hasn't been tampered with
            curr_hash: pd.Series = pd.util.hash_pandas_object(self._cached_smry_df)
            if not curr_hash.equals(self._hash_for_cached_smry_df):
                raise KeyError("The cached SMRY DataFrame has been tampered with")

            return self._cached_smry_df

        self._cached_smry_df = EnsembleSetModel._get_ensembles_data(
            self._ensembles,
            "load_smry",
            time_index=self._smry_time_index,
            column_keys=self._smry_column_keys,
        )
        self._hash_for_cached_smry_df = pd.util.hash_pandas_object(self._cached_smry_df)

        return self._cached_smry_df

    def load_smry_meta(self) -> pd.DataFrame:
        """Finds metadata for the summary vectors in the ensemble set.
        Note that we assume the same units for all ensembles.
        (meaning that we update/overwrite when checking the next ensemble)
        """

        smry_meta: dict = {}
        for ensemble in self._ensembles:
            smry_meta.update(
                ensemble.load_smry_meta(column_keys=self._smry_column_keys).T.to_dict()
            )
        return pd.DataFrame(smry_meta).transpose()

    def load_csv(self, csv_file: pathlib.Path) -> pd.DataFrame:
        return EnsembleSetModel._get_ensembles_data(
            self._ensembles, "load_csv", csv_file=csv_file
        )

    @property
    def webvizstore(self) -> List[Tuple[Callable, List[Dict]]]:
        store_functions = []
        for ensemble in self._ensembles:
            store_functions.extend(ensemble.webviz_store)
        return store_functions
