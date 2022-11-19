from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import pandas as pd
from webviz_config.utils import StrEnum
from webviz_config.webviz_store import webvizstore

from webviz_subsurface._datainput.fmu_input import scratch_ensemble


class TreeType(StrEnum):
    GRUPTREE = "GRUPTREE"
    BRANPROP = "BRANPROP"


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
        tree_type: Optional[str] = None,
    ):
        self._ens_name = ens_name
        self._ens_path = ens_path
        self._gruptree_file = gruptree_file
        self._tree_type = TreeType(tree_type) if tree_type is not None else None
        self._dataframe = self.read_ensemble_gruptree()

        self._gruptrees_are_equal_over_reals = (
            self._dataframe["REAL"].nunique() == 1
            if not self._dataframe.empty
            else False
        )

    @property
    def dataframe(self) -> pd.DataFrame:
        """Returns a dataframe that will have the following columns:
        * DATE
        * CHILD (node in tree)
        * PARENT (node in tree)
        * KEYWORD (GRUPTREE, WELSPECS or BRANPROP)
        * REAL

        If gruptrees are exactly equal in all realizations then only one tree is
        stored in the dataframe. That means the REAL column will only have one unique value.
        If not, all trees are stored.
        """
        return self._dataframe

    def get_filtered_dataframe(
        self,
        terminal_node: Optional[str] = None,
        excl_well_startswith: Optional[List[str]] = None,
        excl_well_endswith: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """This function returns a sub-set of the rows in the gruptree dataframe
        filtered according to the input arguments:

        - terminal_node: returns the terminal node and all nodes below it in the
        tree (for all realizations and dates)
        - excl_well_startswith: removes WELSPECS rows where CHILD starts with any
        of the entries in the list.
        - excl_well_endswith: removes WELSPECS rows where CHILD ends with any
        of the entries in the list.

        """
        df = self._dataframe

        if terminal_node is not None:

            if terminal_node not in self._dataframe["CHILD"].unique():
                raise ValueError(
                    f"Terminal node '{terminal_node}' not found in 'CHILD' column "
                    "of the gruptree data."
                )
            if terminal_node != "FIELD":
                branch_nodes = self._get_branch_nodes(terminal_node)
                df = self._dataframe[self._dataframe["CHILD"].isin(branch_nodes)]

        def filter_wells(
            dframe: pd.DataFrame, well_name_criteria: Callable
        ) -> pd.DataFrame:
            return dframe[
                (dframe["KEYWORD"] != "WELSPECS")
                | (
                    (dframe["KEYWORD"] == "WELSPECS")
                    & (~well_name_criteria(dframe["CHILD"]))
                )
            ]

        if excl_well_startswith is not None:
            # Filter out WELSPECS rows where CHILD starts with any element in excl_well_startswith
            # Conversion to tuple done outside lambda due to mypy
            excl_well_startswith_tuple = tuple(excl_well_startswith)
            df = filter_wells(
                df, lambda x: x.str.startswith(excl_well_startswith_tuple)
            )

        if excl_well_endswith is not None:
            # Filter out WELSPECS rows where CHILD ends with any element in excl_well_endswith
            # Conversion to tuple done outside lambda due to mypy
            excl_well_endswith_tuple = tuple(excl_well_endswith)
            df = filter_wells(df, lambda x: x.str.endswith(excl_well_endswith_tuple))

        return df.copy()

    def _get_branch_nodes(self, terminal_node: str) -> List[str]:
        """The function is using recursion to find all wells below the node
        in the three.
        """
        branch_nodes = [terminal_node]

        children = self._dataframe[
            self._dataframe["PARENT"] == terminal_node
        ].drop_duplicates(subset=["CHILD"], keep="first")

        for _, childrow in children.iterrows():
            branch_nodes.extend(self._get_branch_nodes(childrow["CHILD"]))
        return branch_nodes

    @property
    def gruptrees_are_equal_over_reals(self) -> bool:
        """Returns true if gruptrees are exactly equal in all realizations."""
        return self._gruptrees_are_equal_over_reals

    def __repr__(self) -> str:
        """This is necessary for webvizstore to work on objects"""
        return f"""
GruptreeDataModel({self._ens_name!r}, {self._ens_path!r}, {self._gruptree_file!r})
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
    def read_ensemble_gruptree(
        self, df_files: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """Reads the gruptree files for an ensemble from the scratch disk. These
        files can be exported in the FMU workflow using the ECL2CSV
        forward model with subcommand gruptree.

        If tree_type == BRANPROP then GRUPTREE rows are filtered out
        If tree_type == GRUPTREE then BRANPROP rows are filtered out

        If the trees are equal in every realization, only one realization is kept.

        It is possible to pass a dataframe of file names (only columns required is
        REAL and FULLPATH). This is mostly intended for testing. If this is defaulted
        the files are found automatically using the scratch_ensemble.
        """
        if df_files is None:
            ens = scratch_ensemble(
                self._ens_name, str(self._ens_path), filter_file="OK"
            )
            df_files = ens.find_files(self._gruptree_file)

        if df_files.empty:
            return pd.DataFrame()

        # Load all gruptree dataframes and check if they are equal
        compare_columns = ["DATE", "CHILD", "KEYWORD", "PARENT"]
        df_prev = pd.DataFrame()
        dataframes = []
        gruptrees_are_equal = True
        for i, row in df_files.iterrows():
            df_real = pd.read_csv(row["FULLPATH"])
            unique_keywords = df_real["KEYWORD"].unique()

            if self._tree_type is None:
                # if tree_type is None, then we filter out GRUPTREE if BRANPROP
                # exists, if else we do nothing.
                if TreeType.BRANPROP.value in unique_keywords:
                    df_real = df_real[df_real["KEYWORD"] != TreeType.GRUPTREE.value]

            else:
                if self._tree_type.value not in unique_keywords:
                    raise ValueError(
                        f"Keyword {self._tree_type.value} not found in {row['FULLPATH']}"
                    )
                if (
                    self._tree_type == TreeType.GRUPTREE
                    and TreeType.BRANPROP.value in unique_keywords
                ):
                    # Filter out BRANPROP entries
                    df_real = df_real[df_real["KEYWORD"] != TreeType.BRANPROP.value]

                if self._tree_type == TreeType.BRANPROP:
                    # Filter out GRUPTREE entries
                    df_real = df_real[df_real["KEYWORD"] != TreeType.GRUPTREE.value]

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
