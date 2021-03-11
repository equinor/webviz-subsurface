from typing import Optional, Literal
from pathlib import Path
from datetime import datetime

import pandas as pd

from webviz_subsurface._models.ensemble_time_series import (
    EnsembleTimeSeries,
)
from webviz_subsurface._models.ensemble_time_series_impl_inmem_dataframe import (
    EnsembleTimeSeriesImplInMemDataFrame,
)
from webviz_subsurface._models.ensemble_time_series_impl_arrow import (
    EnsembleTimeSeriesImplArrow,
)
from webviz_subsurface._models.ensemble_time_series_impl_naive_parquet import (
    EnsembleTimeSeriesImplNaiveParquet,
)


# -------------------------------------------------------------------------
def _create_synthetic_time_series_obj(storage_dir: Path) -> EnsembleTimeSeries:
    # fmt: off
    INPUT_DATA = [
        ["DATE",                "REAL",  "A",   "B"], 
        [datetime(2021, 12, 20), 0,      1.0, 11.0 ], 
        [datetime(2021, 12, 21), 0,      2.0, 12.0 ], 
        [datetime(2021, 12, 22), 0,      3.0, 13.0 ], 
        [datetime(2021, 12, 20), 1,      4.0, 14.0 ], 
        [datetime(2021, 12, 21), 1,      5.0, 15.0 ], 
        [datetime(2021, 12, 22), 1,      6.0, 16.0 ], 
        [datetime(2021, 12, 23), 1,      7.0, 17.0 ], 
    ] 
    # fmt: on

    impl_to_use: Literal["inmem", "arrow", "parquet"] = "arrow"

    input_df = pd.DataFrame(INPUT_DATA[1:], columns=INPUT_DATA[0])
    ts: Optional[EnsembleTimeSeries]

    if impl_to_use == "inmem":
        ts = EnsembleTimeSeriesImplInMemDataFrame(input_df)

    elif impl_to_use == "arrow":
        EnsembleTimeSeriesImplArrow.write_backing_store_from_ensemble_dataframe(
            storage_dir, "dummy_key", input_df
        )
        ts = EnsembleTimeSeriesImplArrow.from_backing_store(storage_dir, "dummy_key")

    elif impl_to_use == "parquet":
        EnsembleTimeSeriesImplNaiveParquet.write_backing_store_from_ensemble_dataframe(
            storage_dir, "dummy_key", input_df
        )
        ts = EnsembleTimeSeriesImplNaiveParquet.from_backing_store(
            storage_dir, "dummy_key"
        )

    if not ts:
        raise ValueError("Failed to create EnsembleTimeSeries")

    return ts


# -------------------------------------------------------------------------
def test_get_metadata(tmp_path: Path) -> None:

    ts = _create_synthetic_time_series_obj(tmp_path)

    all_vecnames = ts.vector_names()
    assert len(all_vecnames) == 2
    assert all_vecnames == ["A", "B"]

    all_realizations = ts.realizations()
    assert len(all_realizations) == 2

    all_dates = ts.dates()
    assert len(all_dates) == 4

    r0_dates = ts.dates([0])
    r1_dates = ts.dates([1])
    assert len(r0_dates) == 3
    assert len(r1_dates) == 4


# -------------------------------------------------------------------------
def test_get_vectors(tmp_path: Path) -> None:

    ts = _create_synthetic_time_series_obj(tmp_path)

    all_vecnames = ts.vector_names()
    assert len(all_vecnames) == 2
    assert all_vecnames == ["A", "B"]

    valdf = ts.get_vectors_df(["A"])
    assert valdf.shape == (7, 3)
    assert valdf.columns.tolist() == ["DATE", "REAL", "A"]

    valdf = ts.get_vectors_df(["A"], [1])
    assert valdf.shape == (4, 3)
    assert valdf.columns.tolist() == ["DATE", "REAL", "A"]

    valdf = ts.get_vectors_df(["B", "A"], [0])
    assert valdf.shape == (3, 4)
    assert valdf.columns.tolist() == ["DATE", "REAL", "B", "A"]


# -------------------------------------------------------------------------
def test_synthetic_get_vectors_for_date(tmp_path: Path) -> None:

    ts = _create_synthetic_time_series_obj(tmp_path)

    all_dates = ts.dates()
    assert len(all_dates) == 4

    date_to_get = all_dates[0]
    valdf = ts.get_vectors_for_date_df(date_to_get, ["A", "B"])
    assert valdf.shape == (2, 3)
    assert valdf.columns.tolist() == ["REAL", "A", "B"]

    date_to_get = all_dates[0]
    valdf = ts.get_vectors_for_date_df(date_to_get, ["A", "B"], [0])
    assert valdf.shape == (1, 3)
    assert valdf.columns.tolist() == ["REAL", "A", "B"]

    date_to_get = all_dates[0]
    valdf = ts.get_vectors_for_date_df(date_to_get, ["A", "B"], [0])
    assert valdf.shape == (1, 3)
    assert valdf.columns.tolist() == ["REAL", "A", "B"]
