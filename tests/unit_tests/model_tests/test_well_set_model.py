from pathlib import Path

import numpy as np
import pytest
import xtgeo

from webviz_subsurface._models import WellSetModel


@pytest.mark.usefixtures("app")
def test_well_set_model(testdata_folder: Path) -> None:
    wellfiles = [
        testdata_folder / "reek_test_data" / "observed_data" / "wells" / well
        for well in ["OP_1.w", "OP_2.w", "OP_3.w", "OP_4.w", "OP_5.w", "OP_6.w"]
    ]

    wmodel = WellSetModel(wellfiles=wellfiles)
    assert set(wmodel.well_names) == set(
        ["OP_1", "OP_2", "OP_3", "OP_4", "OP_5", "OP_6"]
    )
    for name, well in wmodel.wells.items():
        assert isinstance(name, str)
        assert isinstance(well, xtgeo.Well)
    op_6 = wmodel.get_well("OP_6")
    assert isinstance(op_6, xtgeo.Well)
    assert op_6.name == "OP_6"


@pytest.mark.usefixtures("app")
def test_logs(testdata_folder: Path) -> None:
    wmodel = WellSetModel(
        wellfiles=[
            testdata_folder / "reek_test_data" / "observed_data" / "wells" / "OP_6.w"
        ],
        zonelog="Zonelog",
    )
    well = wmodel.get_well("OP_6")
    assert well.zonelogname == "Zonelog"


@pytest.mark.usefixtures("app")
def test_tvd_truncation(testdata_folder: Path) -> None:
    wmodel = WellSetModel(
        wellfiles=[
            testdata_folder / "reek_test_data" / "observed_data" / "wells" / "OP_6.w"
        ],
        tvdmin=1000,
        tvdmax=1500,
    )
    well = wmodel.get_well("OP_6")
    assert well.dataframe["Z_TVDSS"].min() >= 1000
    assert well.dataframe["Z_TVDSS"].max() <= 1501


@pytest.mark.usefixtures("app")
def test_get_fence(testdata_folder: Path) -> None:
    wmodel = WellSetModel(
        wellfiles=[
            testdata_folder / "reek_test_data" / "observed_data" / "wells" / "OP_6.w"
        ],
        zonelog="Zonelog",
    )
    fence = wmodel.get_fence("OP_6")
    assert isinstance(fence, np.ndarray)
    # Test horizontal length
    assert int(fence[:, 3].min()) == -40
    assert int(fence[:, 3].max()) == 2713
    # Test tvd
    assert int(fence[:, 2].min()) == 1
    assert int(fence[:, 2].max()) == 1643
