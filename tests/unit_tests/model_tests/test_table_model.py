from pathlib import Path

import pandas as pd
import pytest


from webviz_subsurface._models import table_model_factory
from webviz_subsurface._models.table_model import EnsembleTableModel
from webviz_subsurface._models.table_model import EnsembleTableModelSet
from webviz_subsurface._models.table_model_implementations import (
    EnsembleTableModel_dataFrameBacked,
)


def test_create_EnsembleTableModel_dataFrameBacked(testdata_folder: Path) -> None:
    df = pd.read_csv(testdata_folder / "aggregated_data" / "smry.csv")
    model = EnsembleTableModel_dataFrameBacked(df)

    assert len(model.column_names()) == 17
    assert model.column_names()[0] == "DATE"
    assert model.column_names()[16] == "YEARS"

    assert len(model.realizations()) == 40

    valdf = model.get_column_values_df("YEARS")
    assert len(valdf.columns) == 2
    assert valdf.columns[0] == "REAL"
    assert valdf.columns[1] == "YEARS"
    assert valdf["REAL"].nunique() == 40

    valarr = model.get_column_values_numpy("YEARS")
    assert len(valarr) == 40

    valarr = model.get_column_values_numpy("REAL", [0, 39, 10])
    assert len(valarr) == 3
    assert valarr[0][0] == 0
    assert valarr[0][-1] == 0
    assert valarr[1][0] == 39
    assert valarr[1][-1] == 39
    assert valarr[2][0] == 10
    assert valarr[2][-1] == 10


def test_create_EnsembleTableModelSet(testdata_folder: Path) -> None:
    modelset = table_model_factory.create_model_set_from_aggregated_csv_file(
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


# def get_data_df(testdata_folder: Path) -> pd.DataFrame:
#    return pd.read_csv(testdata_folder / "aggregated_data" / "smry.csv")
#
# def test_required_columns() -> None:
#    with pytest.raises(KeyError):
#        TableModel(dataframe=pd.DataFrame())
#    with pytest.raises(KeyError):
#        TableModel(dataframe=pd.DataFrame(columns=["ENSEMBLE"]))
#    with pytest.raises(KeyError):
#        TableModel(dataframe=pd.DataFrame(columns=["REAL"]))
#
#
# def test_init(testdata_folder: Path):
#    model = TableModel(get_data_df(testdata_folder))
#
#
# def test_ensemble_names(testdata_folder: Path):
#    model = TableModel(get_data_df(testdata_folder))
#    assert model.ensembles == ["iter-0"]