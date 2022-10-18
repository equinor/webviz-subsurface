from pathlib import Path

import pandas as pd
import pytest
from pandas._testing import assert_frame_equal

from webviz_subsurface._models.gruptree_model import GruptreeModel


@pytest.mark.usefixtures("app")
def test_gruptree_model(testdata_folder):

    ens_path = Path(testdata_folder) / "01_drogon_ahm" / "realization-*" / "iter-0"
    gruptree_file = "share/results/tables/gruptree.csv"

    model = GruptreeModel(
        ens_name="iter-0", ens_path=ens_path, gruptree_file=gruptree_file
    )

    # Load gruptree table from realization-0 and compare with
    # the dataframe from the gruptree_model
    r0_path = str(ens_path).replace("*", "0")
    exp_dframe = pd.read_csv(f"{r0_path}/{gruptree_file}")
    exp_dframe["DATE"] = pd.to_datetime(exp_dframe["DATE"])
    exp_dframe = exp_dframe.where(pd.notnull(exp_dframe), None)
    check_columns = ["DATE", "CHILD", "KEYWORD", "PARENT"]

    assert_frame_equal(model.dataframe[check_columns], exp_dframe[check_columns])
