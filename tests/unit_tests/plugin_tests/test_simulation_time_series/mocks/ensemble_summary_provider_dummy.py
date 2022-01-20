import datetime
from typing import List, Optional, Sequence

import pandas as pd

from webviz_subsurface._providers import (
    EnsembleSummaryProvider,
    Frequency,
    VectorMetadata,
)


class EnsembleSummaryProviderDummy(EnsembleSummaryProvider):
    """Class for EnsembleSummaryProvider mock implementations

    Creates dummy class implementing all methods in EnsembleSummaryProvider with
    NotImplementedError. Derived class is responsible to override necessary methods
    to obtain wanted functionality
    """

    #####################################################e
    #
    # Interface methods raise NotImplementedError
    #
    #####################################################

    def vector_names(self) -> List[str]:
        raise NotImplementedError("Method not implemented for mock!")

    def realizations(self) -> List[int]:
        raise NotImplementedError("Method not implemented for mock!")

    def vector_metadata(self, vector_name: str) -> Optional[VectorMetadata]:
        raise NotImplementedError("Method not implemented for mock!")

    def vector_names_filtered_by_value(
        self,
        exclude_all_values_zero: bool = False,
        exclude_constant_values: bool = False,
    ) -> List[str]:
        raise NotImplementedError("Method not implemented for mock!")

    def dates(
        self,
        resampling_frequency: Optional[Frequency],
        realizations: Optional[Sequence[int]] = None,
    ) -> List[datetime.datetime]:
        raise NotImplementedError("Method not implemented for mock!")

    def supports_resampling(self) -> bool:
        raise NotImplementedError("Method not implemented for mock!")

    def get_vectors_df(
        self,
        vector_names: Sequence[str],
        resampling_frequency: Optional[Frequency],
        realizations: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:
        raise NotImplementedError("Method not implemented for mock!")

    def get_vectors_for_date_df(
        self,
        date: datetime.datetime,
        vector_names: Sequence[str],
        realizations: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:
        raise NotImplementedError("Method not implemented for mock!")
