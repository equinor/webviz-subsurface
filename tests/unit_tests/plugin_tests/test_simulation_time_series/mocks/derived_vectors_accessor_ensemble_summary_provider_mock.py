from typing import List, Optional, Sequence

import pandas as pd

from webviz_subsurface._providers import Frequency

from ....mocks.ensemble_summary_provider_dummy import EnsembleSummaryProviderDummy


class EnsembleSummaryProviderMock(EnsembleSummaryProviderDummy):
    """Mock implementation of EnsembleSummaryProvider for testing derived
    ensemble vectors accessor.

    Implements necessary methods for obtaining wanted test data
    """

    def __init__(self, df: pd.DataFrame) -> None:
        super().__init__()
        self._df = df
        self._vectors: List[str] = [
            elm for elm in df.columns if elm not in ["DATE", "REAL"]
        ]
        self._realizations: List[int] = list(df["REAL"]) if "REAL" in df.columns else []

    #####################################
    #
    # Override methods
    #
    #####################################
    def supports_resampling(self) -> bool:
        return False

    def realizations(self) -> List[int]:
        return self._realizations

    def vector_names(self) -> List[str]:
        return self._vectors

    def get_vectors_df(
        self,
        vector_names: Sequence[str],
        __resampling_frequency: Optional[Frequency],
        realizations: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:
        for elm in vector_names:
            if elm not in self._vectors:
                raise ValueError(
                    f'Requested vector "{elm}" not among provider vectors!'
                )
        if realizations:
            # Note: Reset index as providers reset index counter when filtering
            # realization query.
            output = (
                self._df[["DATE", "REAL"] + list(vector_names)]
                .loc[self._df["REAL"].isin(realizations)]
                .reset_index()
            )
            output.drop("index", inplace=True, axis=1)
            return output
        return self._df[["DATE", "REAL"] + list(vector_names)]
