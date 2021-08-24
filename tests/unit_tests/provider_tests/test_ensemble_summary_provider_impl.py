import sys
from pathlib import Path
from datetime import datetime
from datetime import date

if sys.version_info >= (3, 8):
    from typing import Optional, Literal
else:
    from typing import Optional
    from typing_extensions import Literal

import pytest
from _pytest.fixtures import SubRequest

import pandas as pd

from webviz_subsurface._providers.ensemble_summary_provider import (
    EnsembleSummaryProvider,
)
from webviz_subsurface._providers.ensemble_summary_provider_impl_arrow import (
    EnsembleSummaryProviderImplArrow,
)
from webviz_subsurface._providers.ensemble_summary_provider_impl_parquet import (
    EnsembleSummaryProviderImplParquet,
)
from webviz_subsurface._providers.ensemble_summary_provider_impl_inmem_parquet import (
    EnsembleSummaryProviderImplInMemParquet,
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

# -------------------------------------------------------------------------
@pytest.fixture(
    params=[INPUT_DATA_DATETIME, INPUT_DATA_AFTER_2262, INPUT_DATA_DATE, INPUT_DATA_STR]
)
# @pytest.fixture(params=[INPUT_DATA_DATETIME])
def input_data(request: SubRequest) -> list:
    return request.param


# -------------------------------------------------------------------------
def _create_provider_obj_with_data(
    impl_to_use: Literal["arrow", "parquet", "inmem_parquet"],
    input_df: pd.DataFrame,
    storage_dir: Path,
) -> EnsembleSummaryProvider:

    new_provider: Optional[EnsembleSummaryProvider]

    if impl_to_use == "arrow":
        EnsembleSummaryProviderImplArrow.write_backing_store_from_ensemble_dataframe(
            storage_dir, "dummy_key", input_df
        )
        new_provider = EnsembleSummaryProviderImplArrow.from_backing_store(
            storage_dir, "dummy_key"
        )
    elif impl_to_use == "parquet":
        EnsembleSummaryProviderImplParquet.write_backing_store_from_ensemble_dataframe(
            storage_dir, "dummy_key", input_df
        )
        new_provider = EnsembleSummaryProviderImplParquet.from_backing_store(
            storage_dir, "dummy_key"
        )
    elif impl_to_use == "inmem_parquet":
        EnsembleSummaryProviderImplInMemParquet.write_backing_store_from_ensemble_dataframe(
            storage_dir, "dummy_key", input_df
        )
        new_provider = EnsembleSummaryProviderImplInMemParquet.from_backing_store(
            storage_dir, "dummy_key"
        )

    if not new_provider:
        raise ValueError("Failed to create EnsembleSummaryProvider")

    return new_provider


# -------------------------------------------------------------------------
@pytest.fixture(params=["arrow", "parquet", "inmem_parquet"])
# @pytest.fixture(params=["arrow"])
def provider(
    request: SubRequest, input_data: list, tmp_path: Path
) -> EnsembleSummaryProvider:

    input_df = pd.DataFrame(input_data[1:], columns=input_data[0])
    impl_to_use = request.param

    return _create_provider_obj_with_data(impl_to_use, input_df, tmp_path)


# -------------------------------------------------------------------------
def test_get_metadata(provider: EnsembleSummaryProvider) -> None:

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

    all_realizations = provider.realizations()
    assert len(all_realizations) == 2

    all_dates = provider.dates()
    assert len(all_dates) == 2
    assert isinstance(all_dates[0], datetime)

    r0_dates = provider.dates([0])
    r1_dates = provider.dates([1])
    assert len(r0_dates) == 1
    assert len(r1_dates) == 2


# -------------------------------------------------------------------------
def test_get_vectors(provider: EnsembleSummaryProvider) -> None:

    all_vecnames = provider.vector_names()
    assert len(all_vecnames) == 3

    vecdf = provider.get_vectors_df(["A"])
    assert vecdf.shape == (3, 3)
    assert vecdf.columns.tolist() == ["DATE", "REAL", "A"]

    sampleddate = vecdf["DATE"][0]
    assert isinstance(sampleddate, datetime)

    vecdf = provider.get_vectors_df(["A"], [1])
    assert vecdf.shape == (2, 3)
    assert vecdf.columns.tolist() == ["DATE", "REAL", "A"]

    vecdf = provider.get_vectors_df(["C", "A"], [0])
    assert vecdf.shape == (1, 4)
    assert vecdf.columns.tolist() == ["DATE", "REAL", "C", "A"]


# -------------------------------------------------------------------------
def test_get_vectors_for_date(provider: EnsembleSummaryProvider) -> None:

    all_dates = provider.dates()
    assert len(all_dates) == 2

    date_to_get = all_dates[0]
    assert isinstance(date_to_get, datetime)

    vecdf = provider.get_vectors_for_date_df(date_to_get, ["A"])
    assert vecdf.shape == (2, 2)
    assert vecdf.columns.tolist() == ["REAL", "A"]

    date_to_get = all_dates[0]
    vecdf = provider.get_vectors_for_date_df(date_to_get, ["A", "C"], [0])
    assert vecdf.shape == (1, 3)
    assert vecdf.columns.tolist() == ["REAL", "A", "C"]

    date_to_get = all_dates[0]
    vecdf = provider.get_vectors_for_date_df(date_to_get, ["A", "Z"], [0])
    assert vecdf.shape == (1, 3)
    assert vecdf.columns.tolist() == ["REAL", "A", "Z"]
