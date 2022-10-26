import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import pytest
from pandas._testing import assert_frame_equal

from webviz_subsurface._models.gruptree_model import GruptreeModel, TreeType

CHECK_COLUMNS = ["DATE", "CHILD", "KEYWORD", "PARENT"]
ENSEMBLE = "01_drogon_ahm"
GRUPTREE_FILE = "share/results/tables/gruptree.csv"


@pytest.fixture(name="gruptree_model")
def fixture_model(testdata_folder) -> GruptreeModel:
    ens_path = Path(testdata_folder) / ENSEMBLE / "realization-*" / "iter-0"
    return GruptreeModel(
        ens_name="iter-0",
        ens_path=ens_path,
        gruptree_file=GRUPTREE_FILE,
        tree_type="GRUPTREE",
    )


# Mock class that loads local csv file
class MockGruptreeModel(GruptreeModel):
    # pylint: disable=super-init-not-called
    def __init__(self, tree_type: Optional[TreeType] = None):
        self._tree_type = tree_type
        df_files = pd.DataFrame([{"REAL": 0, "FULLPATH": "tests/data/gruptree.csv"}])
        self._dataframe = self.read_ensemble_gruptree(df_files=df_files)


@pytest.mark.usefixtures("app")
def test_gruptree_model_init(testdata_folder, gruptree_model: GruptreeModel):

    # Check that there is only one REAL (means that the gruptree is
    # the same for all realizations)
    assert gruptree_model.dataframe["REAL"].nunique() == 1

    # Load gruptree table from realization-0 and compare with
    # the dataframe from the gruptree_model
    r0_path = f"{testdata_folder}/{ENSEMBLE}/realization-0/iter-0/{GRUPTREE_FILE}"
    exp_df = pd.read_csv(r0_path)
    exp_df["DATE"] = pd.to_datetime(exp_df["DATE"])
    exp_df = exp_df.where(pd.notnull(exp_df), None)

    assert_frame_equal(gruptree_model.dataframe[CHECK_COLUMNS], exp_df[CHECK_COLUMNS])


@pytest.mark.usefixtures("app")
def test_get_filtered_dataframe(gruptree_model: GruptreeModel):

    # Test the get_filtered_dataframe function with terminal node different than FIELD
    filtered_df = gruptree_model.get_filtered_dataframe(terminal_node="OP")
    filtered_df = filtered_df[
        filtered_df["DATE"] == filtered_df["DATE"].max()
    ].reset_index()
    exp_filtered_df = pd.DataFrame(
        columns=["DATE", "CHILD", "KEYWORD", "PARENT"],
        data=[
            [datetime.datetime(year=2018, month=11, day=17), "OP", "GRUPTREE", "FIELD"],
            [datetime.datetime(year=2018, month=11, day=17), "A1", "WELSPECS", "OP"],
            [datetime.datetime(year=2018, month=11, day=17), "A2", "WELSPECS", "OP"],
            [datetime.datetime(year=2018, month=11, day=17), "A3", "WELSPECS", "OP"],
            [datetime.datetime(year=2018, month=11, day=17), "A4", "WELSPECS", "OP"],
        ],
    )
    assert_frame_equal(filtered_df[CHECK_COLUMNS], exp_filtered_df)

    # Test excl_wells_startswith and excl_wells_endswith
    assert set(
        gruptree_model.get_filtered_dataframe(
            excl_well_startswith=["R_"],
            excl_well_endswith=["3", "5"],
        )["CHILD"].unique()
    ) == {"FIELD", "OP", "RFT", "WI", "A1", "A2", "A4", "A6"}


def test_tree_type_filtering():

    mock_model = MockGruptreeModel(tree_type=TreeType.GRUPTREE)
    assert "BRANPROP" not in mock_model.dataframe["KEYWORD"].unique()

    mock_model = MockGruptreeModel(tree_type=TreeType.BRANPROP)
    assert "GRUPTREE" not in mock_model.dataframe["KEYWORD"].unique()

    # If tree_type is defaulted then the BRANPROP tree is selected
    mock_model = MockGruptreeModel()
    assert "GRUPTREE" not in mock_model.dataframe["KEYWORD"].unique()
