from pathlib import Path

import pandas as pd
import pytest


from webviz_subsurface._models import TableModel


def get_data_df(testdata_folder: Path) -> pd.DataFrame:

    return pd.read_csv(testdata_folder / "aggregated_data" / "smry.csv")


def test_required_columns() -> None:
    with pytest.raises(KeyError):
        TableModel(dataframe=pd.DataFrame())
    with pytest.raises(KeyError):
        TableModel(dataframe=pd.DataFrame(columns=["ENSEMBLE"]))
    with pytest.raises(KeyError):
        TableModel(dataframe=pd.DataFrame(columns=["REAL"]))


def test_init(testdata_folder: Path):
    model = TableModel(get_data_df(testdata_folder))


def test_ensemble_names(testdata_folder: Path):
    model = TableModel(get_data_df(testdata_folder))
    assert model.ensembles == ["iter-0"]