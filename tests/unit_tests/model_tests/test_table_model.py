from typing import List, Dict, Optional
from pathlib import Path

import pandas as pd
import numpy as np

from webviz_subsurface._models.table_model import EnsembleTableModel
from webviz_subsurface._models.table_model_implementations import (
    EnsembleTableModelImplInMemDataFrame,
)
from webviz_subsurface._models.table_model_implementations import (
    EnsembleTableModelImplArrow,
)
from webviz_subsurface._models.table_model_factory import EnsembleTableModelFactory


# -------------------------------------------------------------------------
def _create_synthetic_table_model_obj(
    storage_dir: Path,
) -> EnsembleTableModel:
    # fmt: off
    INPUT_DATA = [
        ["REAL",  "A",   "B",  "STR" ], 
        [     0,  1.0,  11.0,   "aa" ], 
        [     0,  2.0,  12.0,   "bb" ], 
        [     0,  3.0,  13.0,   "cc" ], 
        [     1,  4.0,  14.0,   "dd" ], 
        [     1,  5.0,  15.0,   "ee" ], 
        [     1,  6.0,  16.0,   "ff" ], 
        [     1,  7.0,  17.0,   "gg" ], 
    ] 
    # fmt: on

    input_df = pd.DataFrame(INPUT_DATA[1:], columns=INPUT_DATA[0])

    use_in_mem_backing = False
    tm: Optional[EnsembleTableModel]
    if use_in_mem_backing:
        tm = EnsembleTableModelImplInMemDataFrame(input_df)
    else:
        EnsembleTableModelImplArrow.write_backing_store_from_ensemble_dataframe(
            storage_dir, "dummy_key", input_df
        )
        tm = EnsembleTableModelImplArrow.from_backing_store(storage_dir, "dummy_key")

    if not tm:
        raise ValueError("Failed to create EnsembleTableModel")

    return tm


# -------------------------------------------------------------------------
def test_synthetic_get_values_df(testdata_folder: Path) -> None:
    model = _create_synthetic_table_model_obj(testdata_folder)
    assert model.column_names() == ["A", "B", "STR"]
    assert model.realizations() == [0, 1]

    df = model.get_column_values_df("A")
    assert df.shape == (7, 2)
    assert df.columns.tolist() == ["REAL", "A"]

    df = model.get_column_values_df("STR", [1])
    assert df.shape == (4, 2)
    assert df.columns.tolist() == ["REAL", "STR"]


# -------------------------------------------------------------------------
def test_synthetic_get_values_numpy(testdata_folder: Path) -> None:
    model = _create_synthetic_table_model_obj(testdata_folder)
    assert model.column_names() == ["A", "B", "STR"]
    assert model.realizations() == [0, 1]

    arrlist: List[np.ndarray] = model.get_column_values_numpy("A")
    assert len(arrlist) == 2
    assert len(arrlist[0]) == 3
    assert len(arrlist[1]) == 4

    arrlist = model.get_column_values_numpy("STR", [0])
    assert len(arrlist) == 1
    arr = arrlist[0]
    assert arr[0] == "aa"
    assert arr[2] == "cc"


# -------------------------------------------------------------------------
def test_create_from_aggregated_csv_file_smry_csv(
    testdata_folder: Path, tmp_path: Path
) -> None:
    factory = EnsembleTableModelFactory(tmp_path, allow_storage_writes=True)
    modelset = factory.create_model_set_from_aggregated_csv_file(
        testdata_folder / "aggregated_data" / "smry.csv"
    )

    assert modelset.ensemble_names() == ["iter-0"]
    model = modelset.ensemble("iter-0")

    assert len(model.column_names()) == 17
    assert model.column_names()[0] == "DATE"
    assert model.column_names()[16] == "YEARS"

    assert len(model.realizations()) == 40

    valdf = model.get_column_values_df("YEARS")
    assert len(valdf.columns) == 2
    assert valdf.columns[0] == "REAL"
    assert valdf.columns[1] == "YEARS"
    assert valdf["REAL"].nunique() == 40

    arrlist: List[np.ndarray] = model.get_column_values_numpy("YEARS")
    assert len(arrlist) == 40

    arrlist = model.get_column_values_numpy("REAL", [0, 39, 10])
    assert len(arrlist) == 3
    assert arrlist[0][0] == 0
    assert arrlist[0][-1] == 0
    assert arrlist[1][0] == 39
    assert arrlist[1][-1] == 39
    assert arrlist[2][0] == 10
    assert arrlist[2][-1] == 10


# -------------------------------------------------------------------------
def test_create_from_aggregated_csv_file_smry_hm(
    testdata_folder: Path, tmp_path: Path
) -> None:
    factory = EnsembleTableModelFactory(tmp_path, allow_storage_writes=True)
    modelset = factory.create_model_set_from_aggregated_csv_file(
        testdata_folder / "aggregated_data" / "smry_hm.csv"
    )

    assert modelset.ensemble_names() == ["iter-0", "iter-3"]
    model = modelset.ensemble("iter-0")

    assert len(model.column_names()) == 474
    assert model.column_names()[0] == "DATE"
    assert model.column_names()[1] == "BPR:15,28,1"
    assert model.column_names()[473] == "YEARS"

    assert len(model.realizations()) == 10

    valdf = model.get_column_values_df("DATE")
    assert len(valdf.columns) == 2
    assert valdf.columns[0] == "REAL"
    assert valdf.columns[1] == "DATE"
    assert valdf["REAL"].nunique() == 10


# -------------------------------------------------------------------------
def test_create_from_per_realization_csv_file(
    testdata_folder: Path, tmp_path: Path
) -> None:

    ensembles: Dict[str, str] = {
        "iter-0": str(testdata_folder / "reek_history_match/realization-*/iter-0"),
        "iter-1": str(testdata_folder / "reek_history_match/realization-*/iter-1"),
        "iter-2": str(testdata_folder / "reek_history_match/realization-*/iter-2"),
        "iter-3": str(testdata_folder / "reek_history_match/realization-*/iter-3"),
    }

    csvfile = "share/results/tables/rft.csv"

    factory = EnsembleTableModelFactory(tmp_path, allow_storage_writes=True)
    modelset = factory.create_model_set_from_per_realization_csv_file(
        ensembles, csvfile
    )

    assert modelset.ensemble_names() == ["iter-0", "iter-1", "iter-2", "iter-3"]
    model = modelset.ensemble("iter-0")

    all_column_names = model.column_names()
    # print(all_column_names)
    assert len(model.column_names()) == 13

    # The "ordering" of realizations in FMU are arbitrary which in turn means
    # that the order of the columns in dataframe from FMU isn't stable
    # assert model.column_names()[0] == "CONBPRES"
    # assert model.column_names()[5] == "DATE"
    # assert model.column_names()[12] == "WELLMODEL"

    assert len(model.realizations()) == 10

    # Access as dataframe
    valdf = model.get_column_values_df("CONIDX", [2])
    assert valdf.shape == (49, 2)
    assert valdf.columns[0] == "REAL"
    assert valdf.columns[1] == "CONIDX"
    assert valdf["REAL"].unique() == [2]
    assert valdf["CONIDX"].nunique() == 9
    assert sorted(valdf["CONIDX"].unique()) == [1, 2, 3, 4, 5, 6, 7, 8, 9]

    # Access as numpy array
    arrlist: List[np.ndarray] = model.get_column_values_numpy("CONIDX", [2])
    assert len(arrlist) == 1
    arr = arrlist[0]
    assert len(arr) == 49
    assert len(np.unique(arr)) == 9
    assert np.unique(arr).tolist() == [1, 2, 3, 4, 5, 6, 7, 8, 9]
