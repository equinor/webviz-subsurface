import abc
from typing import List, Optional, Sequence

import datetime

import pandas as pd

from webviz_subsurface._utils.dataframe_utils import make_date_column_datetime_object


class DerivedVectorsAccessor:
    def __init__(self, accessor_realizations: List[int]) -> None:
        self._accessor_realizations: List[int] = accessor_realizations

    @abc.abstractmethod
    def has_provider_vectors(self) -> bool:
        ...

    @abc.abstractmethod
    def has_per_interval_and_per_day_vectors(self) -> bool:
        ...

    @abc.abstractmethod
    def has_vector_calculator_expressions(self) -> bool:
        ...

    @abc.abstractmethod
    def get_provider_vectors_df(
        self, realizations: Optional[Sequence[int]] = None
    ) -> pd.DataFrame:
        ...

    @abc.abstractmethod
    def create_per_interval_and_per_day_vectors_df(
        self,
        realizations: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:
        ...

    @abc.abstractmethod
    def create_calculated_vectors_df(
        self, realizations: Optional[Sequence[int]] = None
    ) -> pd.DataFrame:
        ...

    def create_valid_realizations_query(
        self, selected_realizations: List[int]
    ) -> Optional[List[int]]:
        """Create realizations query for accessor based on selected realizations.

        `Returns:`
        - None - If all realizations for accessor is selected, i.e. the query is non-filtering
        - List[int] - List of realization numbers existing for the accessor - empty list
        is returned if no realizations exist.
        """
        if set(self._accessor_realizations).issubset(set(selected_realizations)):
            return None
        return [
            realization
            for realization in selected_realizations
            if realization in self._accessor_realizations
        ]

    @staticmethod
    def _create_relative_to_date_df_2(
        df: pd.DataFrame, relative_date: datetime.datetime
    ) -> pd.DataFrame:
        """
        Create dataframe where data for relative_date is subtracted from respective
        vector data.

        I.e. Subtract vector data for set of realizations at give date from vectors
        for all dates present in dataframe.

        `Input:`
        * df - `Columns` in dataframe: ["DATE", "REAL", vector1, ..., vectorN]

        NOTE: THIS IS A PROTOTYPE, WHICH IS NOT OPTIMAL FOR PERFORMANCE

        TODO:
        - OPTIMIZE CODE/ REFACTOR
        - HOW TO HANDLE IF relative_date does not exist in one REAL? .dropna()?
        """
        output_df = pd.DataFrame(columns=df.columns)
        _relative_date_df: pd.DataFrame = (
            df.loc[df["DATE"] == relative_date]
            .drop(columns=["DATE"])
            .set_index(["REAL"])
        )
        if _relative_date_df.empty:
            # TODO: Return empty dataframe with columns and no rows or input df?
            return output_df

        for __, _df in df.groupby("DATE"):
            # TODO: Simplify code within loop?
            _date = _df["DATE"]
            _date_index = pd.Index(_date)

            _df.drop(columns=["DATE"], inplace=True)
            _df.set_index(["REAL"], inplace=True)

            # TODO: What if "REAL" is not matching between _relative_date_df and _df
            res = _df.sub(_relative_date_df)  # .dropna(axis=0, how="any")
            res.reset_index(inplace=True)
            res.set_index(_date_index, inplace=True)
            res.reset_index(inplace=True)

            output_df = pd.concat([output_df, res], ignore_index=True)

        # TODO: Drop sorting?
        output_df.sort_values(["REAL", "DATE"], ignore_index=True, inplace=True)

        make_date_column_datetime_object(output_df)

        return output_df

    @staticmethod
    def _create_relative_to_date_df(
        df: pd.DataFrame, relative_date: datetime.datetime
    ) -> pd.DataFrame:
        """
        Create dataframe where data for relative_date is subtracted from respective
        vector data.

        I.e. Subtract vector data for set of realizations at give date from vectors
        for all dates present in dataframe.

        `Input:`
        * df - `Columns` in dataframe: ["DATE", "REAL", vector1, ..., vectorN]

        NOTE:
        - THIS IS A PROTOTYPE, WHICH IS NOT OPTIMAL FOR PERFORMANCE
        - This function assumes equal reals for each datetime - df.groupby("REAL") and .loc[_relative_date_df["REAL"] == _real]
        needs equal realizations

        TODO:
        - OPTIMIZE CODE/ REFACTOR
        - Possible to perform calc inplace?
        """
        output_df = pd.DataFrame(columns=df.columns)
        _relative_date_df: pd.DataFrame = df.loc[df["DATE"] == relative_date].drop(
            columns=["DATE"]
        )
        if _relative_date_df.empty:
            # TODO: Return empty dataframe with columns and no rows or input df?
            return output_df

        if set(_relative_date_df["REAL"]) != set(df["REAL"]):
            return output_df
            # raise ValueError(f"Missing realizations for relative date {relative_date}!")

        vectors = [elm for elm in df.columns if elm not in ("DATE", "REAL")]
        for _real, _df in df.groupby("REAL"):
            # TODO: Verify loc[_relative_date_df["REAL"] == _real] and iloc[0]
            _relative_date_data = (
                _relative_date_df.loc[_relative_date_df["REAL"] == _real]
                .drop(columns=["REAL"])
                .iloc[0]
            )
            _df[vectors] = _df[vectors].sub(_relative_date_data, axis=1)
            output_df = pd.concat([output_df, _df], ignore_index=True)

        make_date_column_datetime_object(output_df)

        return output_df
