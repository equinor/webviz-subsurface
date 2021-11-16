from typing import List, Optional, Sequence, TypedDict
import datetime

import pandas as pd

from webviz_subsurface._providers import (
    EnsembleSummaryProvider,
    Frequency,
    VectorMetadata,
)


class DeltaEnsembleNamePair(TypedDict):
    ensemble_a: str
    ensemble_b: str


# TODO: Place on class as staticmethod?
def create_delta_ensemble_name(name_pair: DeltaEnsembleNamePair) -> str:
    name_a = name_pair["ensemble_a"]
    name_b = name_pair["ensemble_b"]
    return f"({name_a})-({name_b})"


# TODO: Place on class as staticmethod?
def create_delta_ensemble_names(ensembles: List[DeltaEnsembleNamePair]) -> List[str]:
    return [create_delta_ensemble_name(elm) for elm in ensembles]


class DeltaEnsembleProvider(EnsembleSummaryProvider):
    """
    Class to define a delta ensemble provider which represent a delta calculation
    (subtraction) between two ensembles - A and B.

    Base class is EnsembleSummaryProvider, utilized to provide one single
    interface for ensemble vectors.
    """

    def __init__(
        self,
        ensemble_provider_a: EnsembleSummaryProvider,
        ensemble_provider_b: EnsembleSummaryProvider,
    ) -> None:
        """
        When new EnsembleSummaryProvider is in place, the attributes will change:

        `Input:`
         * ensemble_provider_a: EnsembleSummaryProvider - Summary data provider for ensemble A
         * ensemble_provider_b: EnsembleSummaryProvider - Summary data provider for ensemble B

        NOTE:
        - When providing provider_set:
            + Ensure retreiving ensembles from same provider set - will there be any
              other option?
            + One can ensure same sampling interval
        - When providing provider A and B:
            + Does not need to provide entire provider_set object
            - The ensemble names have to be given separately and "linked" to specific
              provider


        TODO:
        - Consider:
            - Pass provider for ensemble A and B and corresponding names instead?
              Can pass ensemble provider and name as pair/dict e.g. typed dict
        """

        if (
            ensemble_provider_a.supports_resampling()
            != ensemble_provider_b.supports_resampling()
        ):
            raise ValueError(
                f"Ensemble A and B must have same resampling support! "
                f"Ensemble A support resampling: {ensemble_provider_a.supports_resampling()} "
                f"and Ensemble B support resampling: {ensemble_provider_b.supports_resampling()}"
            )

        self.provider_a = ensemble_provider_a
        self.provider_b = ensemble_provider_b

    def vector_names(self) -> List[str]:
        """
        Get common vector names for ensemble A and B

        `Return:` Vector names existing for both ensemble A and B
        """
        return [
            elm
            for elm in self.provider_a.vector_names()
            if elm in self.provider_b.vector_names()
        ]

    def vector_names_filtered_by_value(
        self,
        exclude_all_values_zero: bool = False,
        exclude_constant_values: bool = False,
    ) -> List[str]:
        """
        Get common vector names for ensemble A and B, filtered by value

        `Return:` Vector names existing for both ensemble A and B after filtering
        by values
        """
        return [
            elm
            for elm in self.provider_a.vector_names_filtered_by_value(
                exclude_all_values_zero=exclude_all_values_zero,
                exclude_constant_values=exclude_constant_values,
            )
            if elm
            in self.provider_b.vector_names_filtered_by_value(
                exclude_all_values_zero=exclude_all_values_zero,
                exclude_constant_values=exclude_constant_values,
            )
        ]

    def realizations(self) -> List[int]:
        """
        Get common realizations for ensemble A and B

        `Return:` Realizations existing for both ensemble A and B
        """
        return [
            elm
            for elm in self.provider_a.realizations()
            if elm in self.provider_b.realizations()
        ]

    def vector_metadata(self, vector_name: str) -> Optional[VectorMetadata]:
        """
        Get vector metadata for delta ensemble

        `Return:` Vector metadata if metadata for vector is equal in ensemble A and B,
        otherwise raise exception

        TODO:
        - How to handle mismatching metadata?
             * Is exception the correct solution?
             * Merge units etc and perform "and" on boolean?
             * Always select metadata from one of the providers?
             * NOTE: As of now metadata consistency is verified in __init__ of plugin
        """
        if self.provider_a.vector_metadata(
            vector_name
        ) != self.provider_b.vector_metadata(vector_name):
            raise ValueError(
                f"Metadata for vector, {vector_name}, in ensemble A does not match metadata"
                f"the vector in ensemble B!"
            )
        return self.provider_a.vector_metadata(vector_name)

    def supports_resampling(self) -> bool:
        return (
            self.provider_a.supports_resampling()
            and self.provider_b.supports_resampling()
        )

    def dates(
        self,
        resampling_frequency: Optional[Frequency],
        realizations: Optional[Sequence[int]] = None,
    ) -> List[datetime.datetime]:
        """
        Get common dates for ensemble A and B, with specified realizations

        `Return:` Dates existing for both ensemble A and B in specified realizations

        TODO:
        - Handle invalid realizations? Check if realizations exist for both providers,
          if not raise exception?
        - Ensure if common dates is correct (what happens with missmatching dates?)

        """
        return [
            elm
            for elm in self.provider_a.dates(resampling_frequency, realizations)
            if elm in self.provider_b.dates(resampling_frequency, realizations)
        ]

    def get_vectors_df(
        self,
        vector_names: Sequence[str],
        resampling_frequency: Optional[Frequency],
        realizations: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:
        """
        Get vectors dataframe with delta vectors for ensemble A and B, for common realizations

        `Return:` Dataframe with delta ensemble data for common vectors and realizations in ensemble
        A and B.

        `Output:`
        * DataFrame with columns ["DATE", "REAL", vector1, ..., vectorN]

        `Input:`
        * vector_names: Sequence[str] - Sequence of vector names to get data for
        * resampling_frequency: Optional[Frequency] - Optional resampling frequency
        * realizations: Optional[Sequence[int]] - Optional sequence of realization numbers for
        vectors

        TODO:
        - Verify vector names and realizations exist for both ensemble A and B? Raise exception if
          not?
        - Perform "inner join"? Only obtain matching index ["DATE", "REAL"] - i.e "DATE"-"REAL"
        combination present in only one vector -> neglected
        - Ensure equal dates samples and realizations
        - Ensure same sorting of dates and realizations
        """

        if not vector_names:
            raise ValueError("List of requested vector names is empty")

        # NOTE: Assuming request for existing vector names and realizations
        # NOTE: index order ["REAL","DATE"] to obtain grouping by realization
        # and order by date
        ensemble_a_vectors_df = self.provider_a.get_vectors_df(
            vector_names, resampling_frequency, realizations
        ).set_index(["REAL", "DATE"])
        ensemble_b_vectors_df = self.provider_b.get_vectors_df(
            vector_names, resampling_frequency, realizations
        ).set_index(["REAL", "DATE"])

        # Reset index, group by "REAL" and sort groups by "DATE"
        ensembles_delta_vectors_df = (
            ensemble_a_vectors_df.sub(ensemble_b_vectors_df)
            .reset_index()
            .sort_values(["REAL", "DATE"])
        )

        return ensembles_delta_vectors_df.dropna(axis=0, how="any")

    def get_vectors_for_date_df(
        self,
        __date: datetime.datetime,
        __vector_names: Sequence[str],
        __realizations: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:
        """
        NOT IMPLEMENTED - RAISES EXCEPTION!
        """
        raise Exception("Method not implemented!")
