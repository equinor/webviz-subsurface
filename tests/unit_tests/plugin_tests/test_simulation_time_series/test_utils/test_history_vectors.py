from datetime import datetime
from typing import List, Optional, Sequence

import pandas as pd
import pytest
from pandas._testing import assert_frame_equal

from webviz_subsurface._providers import Frequency
from webviz_subsurface._utils.dataframe_utils import make_date_column_datetime_object

# pylint: disable=line-too-long
from webviz_subsurface.plugins._simulation_time_series._views._subplot_view._utils.history_vectors import (
    create_history_vectors_df,
)

from ....mocks.ensemble_summary_provider_dummy import EnsembleSummaryProviderDummy

# *******************************************************************
#####################################################################
#
# CONFIGURE TESTDATA
#
#####################################################################
# *******************************************************************


class EnsembleSummaryProviderMock(EnsembleSummaryProviderDummy):
    """Mock implementation of EnsembleSummaryProvider for testing of creating history
    vector dataframe

    Implements necessary methods for obtaining wanted test data
    """

    def __init__(self, input_df: pd.DataFrame) -> None:
        super().__init__()

        # Configure dataframe
        self._df = input_df
        self._vector_names: List[str] = list(
            set(self._df.columns) ^ set(["DATE", "REAL"])
        )
        self._realizations: List[int] = list(self._df["REAL"].unique())

    def supports_resampling(self) -> bool:
        return False

    def vector_names(self) -> List[str]:
        return self._vector_names

    def realizations(self) -> List[int]:
        return self._realizations

    def get_vectors_df(
        self,
        vector_names: Sequence[str],
        __resampling_frequency: Optional[Frequency],
        realizations: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:
        if realizations:
            if not set(realizations).issubset(set(self._realizations)):
                raise ValueError(
                    "Requested realizations are not subset of provider realizations!"
                )
            return (
                self._df[["DATE", "REAL"] + list(vector_names)]
                .loc[self._df["REAL"] == realizations[0]]
                .reset_index(drop=True)
            )
        raise ValueError("Expected valid realizations argument for mock!")


# fmt: off
# Vector WA and WB, with corresponding historical vectors WAH and WBH, respectively
# NOTE:
#  - Method utilize guess of historical vector
#       - Assume vectors starting with "F", "G" or "W". Thereby "WA" and "WB" in test
#       - String split on ":" and append "H" on first part, i.e. WA -> WAH,
#         WA:OP_1 -> WAH:OP_1

INPUT_DF = pd.DataFrame(
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
# Data of real = 0 for "WAH"
EXPECTED_WA_HISTORY_DF = pd.DataFrame(
    columns = ["DATE", "REAL", "WA"],
    data = [
        [datetime(2000,1,1),  0,  13.0],
        [datetime(2000,2,1),  0,  23.0],
        [datetime(2000,3,1),  0,  33.0],
        [datetime(2000,4,1),  0,  43.0],
        [datetime(2000,5,1),  0,  53.0],
    ]
)
# Data of real = 0 for "WBH" and "WAH"
EXPECTED_WB_WA_HISTORY_DF = pd.DataFrame(
    columns = ["DATE", "REAL", "WB", "WA"],
    data = [
        [datetime(2000,1,1),  0,  17.0,  13.0],
        [datetime(2000,2,1),  0,  27.0,  23.0],
        [datetime(2000,3,1),  0,  37.0,  33.0],
        [datetime(2000,4,1),  0,  47.0,  43.0],
        [datetime(2000,5,1),  0,  57.0,  53.0],
    ]
)
make_date_column_datetime_object(INPUT_DF)
make_date_column_datetime_object(EXPECTED_WA_HISTORY_DF)
make_date_column_datetime_object(EXPECTED_WB_WA_HISTORY_DF)


# Dates AFTER year 2262!
# NOTE: datetime.datetime after year 2262 is not converted to pd.Timestamp, thus
# no need to make date column datetime object
INPUT_YEAR_2265_DF = pd.DataFrame(
    columns = ["DATE", "REAL",  "WA", "WAH", "WB", "WBH"],
    data = [
        [datetime(2265,1,1),  4,  11.0,  13.0,  15.0,   17.0],
        [datetime(2265,2,1),  4,  21.0,  23.0,  25.0,   27.0],
        [datetime(2265,3,1),  4,  31.0,  33.0,  35.0,   37.0],
        [datetime(2265,4,1),  4,  41.0,  43.0,  45.0,   47.0],
        [datetime(2265,5,1),  4,  51.0,  53.0,  55.0,   57.0],
        [datetime(2265,1,1),  2,  110.0, 115.0, 135.0,  139.0],
        [datetime(2265,2,1),  2,  310.0, 215.0, 235.0,  239.0],
        [datetime(2265,3,1),  2,  410.0, 315.0, 335.0,  339.0],
        [datetime(2265,4,1),  2,  510.0, 415.0, 435.0,  439.0],
        [datetime(2265,5,1),  2,  610.0, 515.0, 535.0,  539.0],
    ]
)
# Data of real = 2 for "WAH"
EXPECTED_YEAR_2265_WA_HISTORY_DF = pd.DataFrame(
    columns = ["DATE", "REAL", "WA"],
    data = [
        [datetime(2265,1,1),  2,  115.0],
        [datetime(2265,2,1),  2,  215.0],
        [datetime(2265,3,1),  2,  315.0],
        [datetime(2265,4,1),  2,  415.0],
        [datetime(2265,5,1),  2,  515.0],
    ]
)
# Data of real = 2 for "WBH" and "WAH"
EXPECTED_YEAR_2265_WB_WA_HISTORY_DF = pd.DataFrame(
    columns = ["DATE", "REAL", "WB", "WA"],
    data = [
        [datetime(2265,1,1),  2,  139.0,  115.0],
        [datetime(2265,2,1),  2,  239.0,  215.0],
        [datetime(2265,3,1),  2,  339.0,  315.0],
        [datetime(2265,4,1),  2,  439.0,  415.0],
        [datetime(2265,5,1),  2,  539.0,  515.0],
    ]
)

# fmt: on


# *******************************************************************
#####################################################################
#
# UNIT TESTS
#
#####################################################################
# *******************************************************************


TEST_CASES = [
    pytest.param(
        EnsembleSummaryProviderMock(INPUT_DF),
        EXPECTED_WA_HISTORY_DF,
        EXPECTED_WB_WA_HISTORY_DF,
    ),
    pytest.param(
        EnsembleSummaryProviderMock(INPUT_YEAR_2265_DF),
        EXPECTED_YEAR_2265_WA_HISTORY_DF,
        EXPECTED_YEAR_2265_WB_WA_HISTORY_DF,
    ),
]


@pytest.mark.parametrize(
    "provider, expected_wa_history_df, expected_wb_wa_history_df", TEST_CASES
)
def test_create_history_vectors_df(
    provider: pd.DataFrame,
    expected_wa_history_df: pd.DataFrame,
    expected_wb_wa_history_df: pd.DataFrame,
) -> None:
    create_wa_history_df = create_history_vectors_df(provider, ["WA"], None)
    create_wb_wa_history_df = create_history_vectors_df(provider, ["WB", "WA"], None)

    assert_frame_equal(create_wa_history_df, expected_wa_history_df)
    assert_frame_equal(create_wb_wa_history_df, expected_wb_wa_history_df)
