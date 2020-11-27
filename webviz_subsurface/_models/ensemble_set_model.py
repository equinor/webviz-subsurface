from typing import Union, Optional, List, Callable, Tuple, Dict, Any
import pathlib

import pandas as pd

from .ensemble_model import EnsembleModel


class EnsembleSetModel:
    """Class to load and manipulate ensemble sets from given paths to
    ensembles on disk"""

    def __init__(
        self,
        ensemble_paths: dict,
        ensemble_set_name: str = "EnsembleSet",
        filter_file: Union[str, None] = "OK",
    ) -> None:
        self.ensemble_paths = ensemble_paths
        self.ensemble_set_name = ensemble_set_name
        self.filter_file = filter_file
        self._webvizstore: List = []
        self.ensembles = [
            EnsembleModel(ens_name, ens_path, filter_file=self.filter_file)
            for ens_name, ens_path in self.ensemble_paths.items()
        ]

    def __repr__(self) -> str:
        return f"EnsembleSetModel: {self.ensemble_paths}"

    @property
    def ens_folders(self) -> dict:
        """Get root folders for ensemble set"""
        return {
            ens: pathlib.Path(ens_path.split("realization")[0])
            for ens, ens_path in self.ensemble_paths.items()
        }

    def _get_ensembles_data(self, func: str, **kwargs: Any) -> pd.DataFrame:
        """Runs the provided function for each ensemble and concats dataframes"""
        dfs = []
        for ensemble in self.ensembles:
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
        return self._get_ensembles_data("load_parameters")

    def load_smry(
        self,
        time_index: Optional[Union[list, str]] = None,
        column_keys: Optional[list] = None,
    ) -> pd.DataFrame:
        return self._get_ensembles_data(
            "load_smry", time_index=time_index, column_keys=column_keys
        )

    def load_smry_meta(
        self,
        column_keys: Optional[list] = None,
    ) -> pd.DataFrame:
        """Finds metadata for the summary vectors in the ensemble set.
        Note that we assume the same units for all ensembles.
        (meaning that we update/overwrite when checking the next ensemble)
        """

        smry_meta: dict = {}
        for ensemble in self.ensembles:
            smry_meta.update(
                ensemble.load_smry_meta(column_keys=column_keys).T.to_dict()
            )
        return pd.DataFrame(smry_meta).transpose()

    def load_csv(self, csv_file: pathlib.Path) -> pd.DataFrame:
        return self._get_ensembles_data("load_csv", csv_file=csv_file)

    @property
    def webvizstore(self) -> List[Tuple[Callable, List[Dict]]]:
        store_functions = []
        for ensemble in self.ensembles:
            store_functions.extend(ensemble.webviz_store)
        return store_functions
