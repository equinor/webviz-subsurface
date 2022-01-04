import datetime
from typing import Dict, List, Optional, Sequence

import pandas as pd

from webviz_subsurface._providers import (
    EnsembleSummaryProvider,
    Frequency,
    VectorMetadata,
)

##################################################################################################
#
# Mock implementations of EnsembleSummaryProvider for testing of ProviderSet class
#
# Only methods utilized by the ProviderSet is implemented for the various EnsembleSummaryProvider
# mock implementations
#
##################################################################################################


class EnsembleSummaryProviderMockBase(EnsembleSummaryProvider):
    """Base class for EnsembleSummaryProvider mock implementations

    Contains implementation of EnsembleSummaryProvider interface methods to utilize in
    unit tests. Unused methods raise NotImplementedError.

    The derived classes are responsible to overwrite attributes and initialize necessary
    attributes to obtain correct functionality.
    """

    def __init__(self) -> None:
        self._vector_metadata_dict: Dict[str, VectorMetadata] = {}
        self._vector_names: List[str] = []
        self._realizations: List[int] = []

    def vector_names(self) -> List[str]:
        return self._vector_names

    def realizations(self) -> List[int]:
        return self._realizations

    def vector_metadata(self, vector_name: str) -> Optional[VectorMetadata]:
        return self._vector_metadata_dict.get(vector_name, None)

    # -- NOT Implemented Methods! ---

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


class FirstEnsembleSummaryProviderMock(EnsembleSummaryProviderMockBase):
    """First mock implementation, with defined vector names, metadata and realization numbers"""

    def __init__(self) -> None:
        super().__init__()

        # Overwrite attributes
        self._vector_metadata_dict = {
            "WWCT:A1": VectorMetadata(
                unit="",
                is_total=False,
                is_rate=True,
                is_historical=False,
                keyword="WWCT",
                wgname="A1",
                get_num=6,
            ),
            "WWCT:A2": VectorMetadata(
                unit="",
                is_total=False,
                is_rate=True,
                is_historical=False,
                keyword="WWCT",
                wgname="A2",
                get_num=7,
            ),
            "WGOR:A1": VectorMetadata(
                unit="SM3/SM3",
                is_total=False,
                is_rate=True,
                is_historical=False,
                keyword="WGOR",
                wgname="A1",
                get_num=6,
            ),
            "WGOR:A2": VectorMetadata(
                unit="SM3/SM3",
                is_total=False,
                is_rate=True,
                is_historical=False,
                keyword="WGOR",
                wgname="A2",
                get_num=7,
            ),
            "WBHP:A1": VectorMetadata(
                unit="BARSA",
                is_total=False,
                is_rate=False,
                is_historical=False,
                keyword="WBHP",
                wgname="A1",
                get_num=6,
            ),
            "WBHP:A2": VectorMetadata(
                unit="BARSA",
                is_total=False,
                is_rate=False,
                is_historical=False,
                keyword="WBHP",
                wgname="A2",
                get_num=7,
            ),
        }
        self._vector_names = list(self._vector_metadata_dict.keys())
        self._realizations = [1, 2, 3, 4, 5]


class SecondEnsembleSummaryProviderMock(EnsembleSummaryProviderMockBase):
    """Second mock implementation, with defined vector names, metadata and realization numbers"""

    def __init__(self) -> None:
        super().__init__()

        # Overwrite attributes
        self._vector_metadata_dict = {
            "WOPT:A1": VectorMetadata(
                unit="SM3",
                is_total=True,
                is_rate=False,
                is_historical=False,
                keyword="WOPT",
                wgname="A1",
                get_num=6,
            ),
            "WOPT:A2": VectorMetadata(
                unit="SM3",
                is_total=False,
                is_rate=True,
                is_historical=False,
                keyword="WOPT",
                wgname="A2",
                get_num=7,
            ),
            "WWCT:A1": VectorMetadata(
                unit="",
                is_total=False,
                is_rate=True,
                is_historical=False,
                keyword="WWCT",
                wgname="A1",
                get_num=6,
            ),
            "WWCT:A2": VectorMetadata(
                unit="",
                is_total=False,
                is_rate=True,
                is_historical=False,
                keyword="WWCT",
                wgname="A2",
                get_num=7,
            ),
            "WOPR:A2": VectorMetadata(
                unit="SM3/DAY",
                is_total=False,
                is_rate=True,
                is_historical=False,
                keyword="WOPR",
                wgname="A2",
                get_num=7,
            ),
            "FGIR": VectorMetadata(
                unit="SM3/DAY",
                is_total=False,
                is_rate=True,
                is_historical=False,
                keyword="FGIR",
                wgname=None,
                get_num=0,
            ),
        }
        self._vector_names = list(self._vector_metadata_dict.keys())
        self._realizations = [1, 2, 4, 5, 8]


class ThirdEnsembleSummaryProviderMock(EnsembleSummaryProviderMockBase):
    """Third mock implementation, with defined vector names, metadata and realization numbers"""

    def __init__(self) -> None:
        super().__init__()

        # Overwrite attributes
        self._vector_metadata_dict = {
            "WGOR:A1": VectorMetadata(
                unit="SM3/SM3",
                is_total=False,
                is_rate=True,
                is_historical=False,
                keyword="WGOR",
                wgname="A1",
                get_num=6,
            ),
            "WGOR:A2": VectorMetadata(
                unit="SM3/SM3",
                is_total=False,
                is_rate=True,
                is_historical=False,
                keyword="WGOR",
                wgname="A2",
                get_num=7,
            ),
            "WOPR:A1": VectorMetadata(
                unit="SM3/DAY",
                is_total=False,
                is_rate=True,
                is_historical=False,
                keyword="WOPR",
                wgname="A1",
                get_num=6,
            ),
            "WOPR:A2": VectorMetadata(
                unit="SM3/DAY",
                is_total=False,
                is_rate=True,
                is_historical=False,
                keyword="WOPR",
                wgname="A2",
                get_num=7,
            ),
            "FGIR": VectorMetadata(
                unit="SM3/DAY",
                is_total=False,
                is_rate=True,
                is_historical=False,
                keyword="FGIR",
                wgname=None,
                get_num=0,
            ),
            "FGIT": VectorMetadata(
                unit="SM3",
                is_total=True,
                is_rate=False,
                is_historical=False,
                keyword="FGIT",
                wgname=None,
                get_num=0,
            ),
        }
        self._vector_names = list(self._vector_metadata_dict.keys())
        self._realizations = [1, 2, 3, 4, 7]


class InconsistentEnsembleSummaryProviderMock(EnsembleSummaryProviderMockBase):
    """Mock implementation to define inconsistent metadata

    Introduces metadata info breaking with the metadata in the three previous implementations

    Contains defined vector names, metadata and realization numbers
    """

    def __init__(self) -> None:
        super().__init__()

        # Overwrite attributes with incorrect metadata to create inconsistency
        self._vector_metadata_dict = {
            "WWCT:A1": VectorMetadata(
                unit="Invalid Unit",
                is_total=False,
                is_rate=False,
                is_historical=False,
                keyword="WWCT",
                wgname="A1",
                get_num=6,
            ),
            "WWCT:A2": VectorMetadata(
                unit="Invalid Unit",
                is_total=False,
                is_rate=False,
                is_historical=False,
                keyword="WWCT",
                wgname="A2",
                get_num=7,
            ),
            "WGOR:A1": VectorMetadata(
                unit="SM3",
                is_total=False,
                is_rate=False,
                is_historical=True,
                keyword="WGOR",
                wgname="A1",
                get_num=6,
            ),
            "WGOR:A2": VectorMetadata(
                unit="SM3",
                is_total=False,
                is_rate=False,
                is_historical=True,
                keyword="WGOR",
                wgname="A2",
                get_num=7,
            ),
        }
        self._vector_names = list(self._vector_metadata_dict.keys())
        self._realizations = [1, 2, 4, 5, 6]
