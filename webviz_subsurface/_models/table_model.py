from typing import List, Dict, Optional, Sequence
from pathlib import Path

import pandas as pd


# fmt: off

class EnsembleTableModel:
    def column_names(self) -> List[str]: ...
    # def has_column(column_name:str) -> bool: ...
    # def has_columns(column_names: List[str]) -> bool: ...
    def realizations(self) -> List[int]: ...

    def get_column_values(self, column_name: str, realizations: Optional[Sequence[int]] = None) -> pd.DataFrame:   ...
    # def get_realizations_based_on_filter(self, filter_column_name: str, column_values: list) -> Sequence[int]: ...

# fmt: on


class EnsembleTableModel_dataFrameBacked(EnsembleTableModel):
    def __init__(self, ensemble_df: pd.DataFrame) -> None:
        # The input DF may contain an ENSEMBLE column, but it is probably an error if
        # There is more than one unique value in it
        if "ENSEMBLE" in ensemble_df:
            if ensemble_df["ENSEMBLE"].nunique() > 1:
                raise KeyError("Input data contains more than one unique ensemble name")

        self._ensemble_df = ensemble_df

        self._column_names: List[str] = [
            col
            for col in list(self._ensemble_df.columns)
            if col not in ["REAL", "ENSEMBLE"]
        ]

    def column_names(self) -> List[str]:
        return self._column_names

    def realizations(self) -> List[int]:
        return list(self._ensemble_df["REAL"].unique())

    def get_column_values(
        self, column_name: str, realizations: Optional[Sequence[int]] = None
    ) -> pd.DataFrame:
        if realizations:
            df = self._ensemble_df.loc[
                self._ensemble_df["REAL"].isin(realizations), ["REAL", column_name]
            ]
        else:
            df = self._ensemble_df.loc[:, ["REAL", column_name]]

        return df


class EnsembleTableModelSet:
    def __init__(self, table_models: Dict[str, EnsembleTableModel]) -> None:
        self._table_models = table_models

    # @staticmethod
    # def fromEnsembleLayout(ensembles: Dict[str, path], csv_file, selector_columns, filter_columns) -> EnsembleSetTableModel:
    #    ensembleset = EnsembleSetTableModel()
    #    for ens in ensemble
    #        new_ensemble = EnsembleModel_ensembleLayout()
    #        ensembleset.add_ensemble(new_ensemble)
    #    return ensembleset

    @staticmethod
    def from_aggregated_csv_file(aggr_csv_file: Path) -> "EnsembleTableModelSet":
        df = pd.read_csv(aggr_csv_file)

        modelset: Dict[str, EnsembleTableModel] = {}

        ensemble_names = df["ENSEMBLE"].unique()
        for ens_name in ensemble_names:
            ensemble_df = df[df["ENSEMBLE"] == ens_name]
            ensemble_table_model = EnsembleTableModel_dataFrameBacked(ensemble_df)
            modelset[ens_name] = ensemble_table_model

        return EnsembleTableModelSet(modelset)

    def ensemble_names(self) -> List[str]:
        return list(self._table_models.keys())

    def ensemble(self, ensemble_name: str) -> EnsembleTableModel:
        return self._table_models[ensemble_name]

    # Tja...
    # def selector_columns(self) -> List:
    # def filter_columns(self) -> List:
