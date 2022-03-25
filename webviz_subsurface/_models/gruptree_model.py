from pathlib import Path
from typing import Callable, Dict, List, Tuple

import pandas as pd
from webviz_config.webviz_store import webvizstore

from webviz_subsurface._datainput.fmu_input import scratch_ensemble


class GruptreeModel:
    """Facilitates loading of gruptree tables. Can be reused in all
    plugins that are using grouptree data and extended with additional
    functionality and filtering options if necessary.
    """

    def __init__(
        self,
        ens_name: str,
        ens_path: Path,
        gruptree_file: str,
        remove_gruptree_if_branprop: bool = True,
    ):
        self._ens_name = ens_name
        self._ens_path = ens_path
        self._gruptree_file = gruptree_file
        self._remove_gruptree_if_branprop = remove_gruptree_if_branprop
        self._dataframe = self.read_ensemble_gruptree()

    @property
    def dataframe(self) -> pd.DataFrame:
        return self._dataframe

    def __repr__(self) -> str:
        """This is necessary for webvizstore to work on objects"""
        return f"""
GruptreeDataModel {self._ens_name} {self._ens_path} {self._gruptree_file}
        """

    @property
    def webviz_store(self) -> Tuple[Callable, List[Dict]]:
        return (
            self.read_ensemble_gruptree,
            [
                {
                    "self": self,
                }
            ],
        )

    @webvizstore
    def read_ensemble_gruptree(self) -> pd.DataFrame:
        """Reads the gruptree files for an ensemble from the scratch disk. These
        files can be exported in the FMU workflow using the ECL2CSV
        forward model with subcommand gruptree.

        If BRANPROP is found in the KEYWORD column, then GRUPTREE rows
        are filtered out.

        If the trees are equal in every realization, only one realization is kept.
        """

        ens = scratch_ensemble(self._ens_name, self._ens_path, filter_file="OK")
        df_files = ens.find_files(self._gruptree_file)

        if df_files.empty:
            return pd.DataFrame()
            # raise ValueError(f"No gruptree file available for ensemble: {ens_name}")

        # Load all gruptree dataframes and check if they are equal
        compare_columns = ["DATE", "CHILD", "KEYWORD", "PARENT"]
        df_prev = pd.DataFrame()
        dataframes = []
        gruptrees_are_equal = True
        for i, row in df_files.iterrows():
            df_real = pd.read_csv(row["FULLPATH"])

            if (
                self._remove_gruptree_if_branprop
                and "BRANPROP" in df_real["KEYWORD"].unique()
            ):
                df_real = df_real[df_real["KEYWORD"] != "GRUPTREE"]

            if (
                i > 0
                and gruptrees_are_equal
                and not df_real[compare_columns].equals(df_prev)
            ):
                gruptrees_are_equal = False
            else:
                df_prev = df_real[compare_columns].copy()

            df_real["REAL"] = row["REAL"]
            dataframes.append(df_real)
        df = pd.concat(dataframes)

        # Return either one or all realization in a common dataframe
        if gruptrees_are_equal:
            df = df[df["REAL"] == df["REAL"].min()]

        df["DATE"] = pd.to_datetime(df["DATE"])

        return df.where(pd.notnull(df), None)
