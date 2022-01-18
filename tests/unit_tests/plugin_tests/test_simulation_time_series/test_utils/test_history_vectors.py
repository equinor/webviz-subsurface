from datetime import datetime
from typing import List, Optional, Sequence

import pandas as pd

from webviz_subsurface._providers import Frequency
from webviz_subsurface.plugins._simulation_time_series.utils.history_vectors import (
    create_history_vectors_df,
)

from ..mocks.ensemble_summary_provider_dummy import EnsembleSummaryProviderDummy

# fmt: off
# Vector WA and WB, with corresponding historical vectors WAH and WBH, respectively
# NOTE:
#  - Method utilize guess of historical vector
#       - Assume vectors starting with "F", "G" or "W". Thereby "WA" and "WB" in test
#       - String split on ":" and append "H" on first part, i.e. WA -> WAH,
#         WA:OP_1 -> WAH:OP_1
#  - Method utilize realization 0! I.e. if realization = 0 does not exist -> crash
TEST_INPUT_DF = pd.DataFrame(
    columns = ["DATE", "REAL",  "WA", "WAH", "WB", "WBH"],
    data = [
        [datetime(2000,1,1),  0,  11.0,  13.0,  15.0,   17.0],
        [datetime(2000,2,1),  0,  21.0,  23.0,  25.0,   27.0],
        [datetime(2000,3,1),  0,  31.0,  33.0,  35.0,   37.0],
        [datetime(2000,4,1),  0,  41.0,  43.0,  45.0,   47.0],
        [datetime(2000,5,1),  0,  51.0,  53.0,  55.0,   57.0],
        [datetime(2000,1,1),  3,  110.0, 115.0, 135.0,  139.0],
        [datetime(2000,2,1),  3,  310.0, 215.0, 235.0,  239.0],
        [datetime(2000,3,1),  3,  410.0, 315.0, 335.0,  339.0],
        [datetime(2000,4,1),  3,  510.0, 415.0, 435.0,  439.0],
        [datetime(2000,5,1),  3,  610.0, 515.0, 535.0,  539.0],
    ]
)
TEST_INPUT_DF["DATE"] = pd.Series(TEST_INPUT_DF["DATE"].dt.to_pydatetime(), dtype=object)
# fmt: on


class EnsembleSummaryProviderMock(EnsembleSummaryProviderDummy):
    """Mock implementation of EnsembleSummaryProvider for testing of creating history
    vector dataframe

    Implements necessary methods for obtaining wanted test data
    """

    def __init__(self) -> None:
        super().__init__()

        # Configure dataframe
        self._df = TEST_INPUT_DF
        self._vector_names = list(set(self._df.columns) ^ set(["DATE", "REAL"]))
        self._realizations = list(self._df["REAL"].unique())

    def supports_resampling(self) -> bool:
        return False

    def realizations(self) -> List[int]:
        return self._realizations

    def vector_names(self) -> List[str]:
        return self._vector_names

    def get_vectors_df(
        self,
        vector_names: Sequence[str],
        __resampling_frequency: Optional[Frequency],
        realizations: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:
        if realizations:
            return self._df[["DATE", "REAL"] + list(vector_names)].loc[
                self._df["REAL"] == realizations[0]
            ]
        raise ValueError("Expected valid realizations argument for mock!")


def test_create_history_vectors_df() -> None:
    """Test function to return the real = 0 data for the historical vector
    with original vector name as column
    """
    # fmt: off
    # Data of real = 0 for "WAH"
    expected_first_history_vectors_df = pd.DataFrame(
        columns = ["DATE", "REAL", "WA"],
        data = [
            [datetime(2000,1,1),  0,  13.0],
            [datetime(2000,2,1),  0,  23.0],
            [datetime(2000,3,1),  0,  33.0],
            [datetime(2000,4,1),  0,  43.0],
            [datetime(2000,5,1),  0,  53.0],
        ]
    )
    expected_first_history_vectors_df["DATE"] = pd.Series(
        expected_first_history_vectors_df["DATE"].dt.to_pydatetime(), dtype=object
    )

    # Data of real = 0 for "WBH" and "WAH"
    expected_second_history_vectors_df = pd.DataFrame(
        columns = ["DATE", "REAL", "WB", "WA"],
        data = [
            [datetime(2000,1,1),  0,  17.0,  13.0],
            [datetime(2000,2,1),  0,  27.0,  23.0],
            [datetime(2000,3,1),  0,  37.0,  33.0],
            [datetime(2000,4,1),  0,  47.0,  43.0],
            [datetime(2000,5,1),  0,  57.0,  53.0],
        ]
    )
    expected_second_history_vectors_df["DATE"] = pd.Series(
        expected_second_history_vectors_df["DATE"].dt.to_pydatetime(), dtype=object
    )
    # fmt: on

    provider = EnsembleSummaryProviderMock()
    first_history_vectors_df = create_history_vectors_df(provider, ["WA"], None)
    second_history_vectors_df = create_history_vectors_df(provider, ["WB", "WA"], None)

    assert list(first_history_vectors_df.columns) == ["DATE", "REAL", "WA"]
    assert first_history_vectors_df.equals(expected_first_history_vectors_df)
    assert list(second_history_vectors_df.columns) == ["DATE", "REAL", "WB", "WA"]
    assert second_history_vectors_df.equals(expected_second_history_vectors_df)
