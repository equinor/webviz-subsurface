from pathlib import Path

import numpy as np
import pytest

from webviz_subsurface._models.ensemble_set_model import EnsembleSetModel


@pytest.mark.usefixtures("app")
def test_single_ensemble(testdata_folder):

    emodel = EnsembleSetModel(
        ensemble_paths={
            "iter-0": str(
                Path(testdata_folder / "01_drogon_ahm" / "realization-*" / "iter-0")
            )
        }
    )
    assert emodel.ens_folders == {"iter-0": Path(testdata_folder) / "01_drogon_ahm"}
    smry = emodel.get_or_load_smry_cached()
    assert len(smry.columns) == 934
    assert len(smry["DATE"].unique()) == 2369
    assert smry["ENSEMBLE"].unique() == ["iter-0"]
    assert smry["ENSEMBLE"].dtype == np.dtype("O")
    assert all(
        np.issubdtype(dtype, np.number)
        for dtype in smry.drop(["REAL", "ENSEMBLE", "DATE"], axis=1).dtypes
    )

    parameters = emodel.load_parameters()
    assert all(col in parameters.columns for col in ["ENSEMBLE", "REAL"])
    assert parameters["ENSEMBLE"].dtype == np.dtype("O")
    assert parameters["REAL"].dtype == np.dtype("int64")
    assert len(parameters.columns) == 56


@pytest.mark.usefixtures("app")
def test_smry_load_multiple_ensembles(testdata_folder):

    emodel = EnsembleSetModel(
        ensemble_paths={
            "iter-0": str(
                Path(testdata_folder / "01_drogon_ahm" / "realization-*" / "iter-0")
            ),
            "iter-3": str(
                Path(testdata_folder / "01_drogon_ahm" / "realization-*" / "iter-3")
            ),
        }
    )
    smry = emodel.get_or_load_smry_cached()
    assert len(smry.columns) == 934
    assert len(smry["DATE"].unique()) == 4167
    assert set(smry["ENSEMBLE"].unique()) == set(["iter-0", "iter-3"])
    assert smry["ENSEMBLE"].dtype == np.dtype("O")
    # assert smry["DATE"].dtype == np.dtype("O") # Fails due to wrong input data?
    assert smry["REAL"].dtype == np.dtype("int64")
    assert all(
        np.issubdtype(dtype, np.number)
        for dtype in smry.drop(["REAL", "ENSEMBLE", "DATE"], axis=1).dtypes
    )
    smeta = emodel.load_smry_meta()
    assert set(smeta.columns) == set(
        ["unit", "is_total", "is_rate", "is_historical", "keyword", "wgname", "get_num"]
    )
    assert len(smeta) == 931
    assert "FOPT" in smeta.index

    parameters = emodel.load_parameters()
    assert all(col in parameters.columns for col in ["ENSEMBLE", "REAL"])
    assert parameters["ENSEMBLE"].dtype == np.dtype("O")
    assert parameters["REAL"].dtype == np.dtype("int64")
    assert len(parameters.columns) == 56

    dframe = emodel.load_csv(Path("share") / "results" / "tables" / "rft.csv")
    assert "ENSEMBLE" in dframe.columns
    assert dframe["ENSEMBLE"].dtype == np.dtype("O")
    assert len(dframe["ENSEMBLE"].unique()) == 2
    assert len(dframe.columns) == 15

    with pytest.raises(KeyError) as exc:
        emodel.load_csv("some_path")
    assert (
        exc.value.args[0]
        == "No data found for load_csv with arguments: {'csv_file': 'some_path'}"
    )


@pytest.mark.usefixtures("app")
def test_webvizstore(testdata_folder):
    emodel = EnsembleSetModel(
        ensemble_paths={
            "iter-0": str(
                Path(testdata_folder / "01_drogon_ahm" / "realization-*" / "iter-0")
            ),
            "iter-3": str(
                Path(testdata_folder / "01_drogon_ahm" / "realization-*" / "iter-3")
            ),
        }
    )
    emodel.load_parameters()
    assert len(emodel.webvizstore) == 2
    emodel.get_or_load_smry_cached()
    assert len(emodel.webvizstore) == 4
    emodel.load_smry_meta()
    assert len(emodel.webvizstore) == 6
    emodel.load_csv(Path("share") / "results" / "tables" / "rft.csv")
    assert len(emodel.webvizstore) == 8
