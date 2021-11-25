from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pytest
from _pytest.fixtures import SubRequest

from webviz_subsurface._providers.ensemble_summary_provider._provider_impl_arrow_presampled import (
    ProviderImplArrowPresampled,
)
from webviz_subsurface._providers.ensemble_summary_provider.ensemble_summary_provider import (
    EnsembleSummaryProvider,
)

# fmt: off
INPUT_DATA_DATETIME = [
    ["DATE",                          "REAL",  "A",  "C",   "Z"],
    [datetime(2021, 12, 20, 23, 59),  0,       10.0,  1.0,  0.0 ],
    [datetime(2021, 12, 20, 23, 59),  1,       12.0,  1.0,  0.0 ],
    [datetime(2021, 12, 21, 22, 58),  1,       13.0,  1.0,  0.0 ],
]

INPUT_DATA_AFTER_2262 = [
    ["DATE",                          "REAL",  "A",  "C",   "Z"],
    [datetime(2500, 12, 20, 23, 59),  0,       10.0,  1.0,  0.0 ],
    [datetime(2500, 12, 20, 23, 59),  1,       12.0,  1.0,  0.0 ],
    [datetime(2500, 12, 21, 22, 58),  1,       13.0,  1.0,  0.0 ],
]

INPUT_DATA_DATE = [
    ["DATE",              "REAL",  "A",  "C",   "Z"],
    [date(2022, 12, 20),  0,       10.0,  1.0,  0.0 ],
    [date(2022, 12, 20),  1,       12.0,  1.0,  0.0 ],
    [date(2022, 12, 21),  1,       13.0,  1.0,  0.0 ],
]

INPUT_DATA_STR = [
    ["DATE",       "REAL",  "A",  "C",   "Z"],
    ["2023-12-20",  0,      10.0,  1.0,  0.0 ],
    ["2023-12-20",  1,      12.0,  1.0,  0.0 ],
    ["2023-12-21",  1,      13.0,  1.0,  0.0 ],
]
# fmt: on


@pytest.fixture(
    name="provider",
    params=[
        INPUT_DATA_DATETIME,
        INPUT_DATA_AFTER_2262,
        INPUT_DATA_DATE,
        INPUT_DATA_STR,
    ],
)
def fixture_provider(request: SubRequest, tmp_path: Path) -> EnsembleSummaryProvider:

    input_py = request.param
    storage_dir = tmp_path

    input_df = pd.DataFrame(input_py[1:], columns=input_py[0])

    ProviderImplArrowPresampled.write_backing_store_from_ensemble_dataframe(
        storage_dir, "dummy_key", input_df
    )
    new_provider = ProviderImplArrowPresampled.from_backing_store(
        storage_dir, "dummy_key"
    )

    if not new_provider:
        raise ValueError("Failed to create EnsembleSummaryProvider")

    return new_provider


def test_get_vector_names(provider: EnsembleSummaryProvider) -> None:

    all_vecnames = provider.vector_names()
    assert len(all_vecnames) == 3
    assert all_vecnames == ["A", "C", "Z"]

    non_const_vec_names = provider.vector_names_filtered_by_value(
        exclude_constant_values=True
    )
    assert len(non_const_vec_names) == 1
    assert non_const_vec_names == ["A"]

    non_zero_vec_names = provider.vector_names_filtered_by_value(
        exclude_all_values_zero=True
    )
    assert len(non_zero_vec_names) == 2
    assert non_zero_vec_names == ["A", "C"]


def test_get_realizations(provider: EnsembleSummaryProvider) -> None:

    all_realizations = provider.realizations()
    assert len(all_realizations) == 2


def test_get_dates(provider: EnsembleSummaryProvider) -> None:

    intersection_of_dates = provider.dates(resampling_frequency=None)
    assert len(intersection_of_dates) == 1
    assert isinstance(intersection_of_dates[0], datetime)

    r0_dates = provider.dates(resampling_frequency=None, realizations=[0])
    r1_dates = provider.dates(resampling_frequency=None, realizations=[1])
    assert len(r0_dates) == 1
    assert len(r1_dates) == 2


def test_get_vectors(provider: EnsembleSummaryProvider) -> None:

    all_vecnames = provider.vector_names()
    assert len(all_vecnames) == 3

    vecdf = provider.get_vectors_df(["A"], resampling_frequency=None)
    assert vecdf.shape == (3, 3)
    assert vecdf.columns.tolist() == ["DATE", "REAL", "A"]

    sampleddate = vecdf["DATE"][0]
    assert isinstance(sampleddate, datetime)

    vecdf = provider.get_vectors_df(["A"], resampling_frequency=None, realizations=[1])
    assert vecdf.shape == (2, 3)
    assert vecdf.columns.tolist() == ["DATE", "REAL", "A"]

    vecdf = provider.get_vectors_df(
        ["C", "A"], resampling_frequency=None, realizations=[0]
    )
    assert vecdf.shape == (1, 4)
    assert vecdf.columns.tolist() == ["DATE", "REAL", "C", "A"]


def test_get_vectors_for_date(provider: EnsembleSummaryProvider) -> None:

    intersection_of_dates = provider.dates(resampling_frequency=None)
    assert len(intersection_of_dates) == 1

    date_to_get = intersection_of_dates[0]
    assert isinstance(date_to_get, datetime)

    vecdf = provider.get_vectors_for_date_df(date_to_get, ["A"])
    assert vecdf.shape == (2, 2)
    assert vecdf.columns.tolist() == ["REAL", "A"]

    date_to_get = intersection_of_dates[0]
    vecdf = provider.get_vectors_for_date_df(date_to_get, ["A", "C"], [0])
    assert vecdf.shape == (1, 3)
    assert vecdf.columns.tolist() == ["REAL", "A", "C"]

    date_to_get = intersection_of_dates[0]
    vecdf = provider.get_vectors_for_date_df(date_to_get, ["A", "Z"], [0])
    assert vecdf.shape == (1, 3)
    assert vecdf.columns.tolist() == ["REAL", "A", "Z"]

    real1_dates = provider.dates(resampling_frequency=None, realizations=[1])
    assert len(real1_dates) == 2
    date_to_get = real1_dates[0]
    vecdf = provider.get_vectors_for_date_df(date_to_get, ["A", "Z"])
    assert vecdf.shape == (2, 3)
    assert vecdf.columns.tolist() == ["REAL", "A", "Z"]
    date_to_get = real1_dates[1]
    vecdf = provider.get_vectors_for_date_df(date_to_get, ["A", "Z"])
    assert vecdf.shape == (1, 3)
    assert vecdf.columns.tolist() == ["REAL", "A", "Z"]
