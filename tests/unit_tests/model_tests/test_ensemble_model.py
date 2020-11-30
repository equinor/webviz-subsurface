from pathlib import Path
import datetime

import pytest
import numpy as np

from webviz_subsurface._models.ensemble_model import EnsembleModel


@pytest.mark.usefixtures("app")
def test_ensemble_set_init(testdata_folder):

    emodel = EnsembleModel(
        ensemble_name="iter-0",
        ensemble_path=Path(testdata_folder)
        / "reek_history_match"
        / "realization-*"
        / "iter-0",
    )
    assert emodel.ens_folder == {"iter-0": f"{testdata_folder}/reek_history_match/"}
    assert emodel.webviz_store == []


@pytest.mark.usefixtures("app")
def test_bad_ensemble_path():
    emodel = EnsembleModel(ensemble_name="iter-0", ensemble_path="some_path")
    with pytest.raises(ValueError) as exception:
        emodel.load_ensemble()
    assert (
        exception.value.args[0]
        == "No realizations found for ensemble iter-0, located at 'some_path'. Aborting..."
    )


@pytest.mark.usefixtures("app")
def test_smry_load(testdata_folder):

    emodel = EnsembleModel(
        ensemble_name="iter-0",
        ensemble_path=Path(testdata_folder)
        / "reek_history_match"
        / "realization-*"
        / "iter-0",
    )
    smry = emodel.load_smry()
    assert len(smry.columns) == 475
    assert len(smry["DATE"].unique()) == 480


@pytest.mark.usefixtures("app")
def test_smry_load_filter_and_dtypes(testdata_folder):

    emodel = EnsembleModel(
        ensemble_name="iter-0",
        ensemble_path=Path(testdata_folder)
        / "reek_history_match"
        / "realization-*"
        / "iter-0",
    )
    smry = emodel.load_smry(column_keys=["FO*"], time_index="yearly")
    assert set(smry.columns) == set(
        [
            "DATE",
            "REAL",
            "FOPRF",
            "FOPRS",
            "FOPRH",
            "FOPTH",
            "FOPR",
            "FOPTS",
            "FOPTF",
            "FOPT",
            "FOIP",
            "FOPP",
        ]
    )
    assert set(smry["DATE"].unique()) == set(
        [
            datetime.date(2000, 1, 1),
            datetime.date(2001, 1, 1),
            datetime.date(2002, 1, 1),
            datetime.date(2003, 1, 1),
            datetime.date(2004, 1, 1),
        ]
    )
    assert smry["DATE"].dtype == np.dtype("O")
    assert smry["REAL"].dtype == np.dtype("int64")
    assert all(
        np.issubdtype(dtype, np.number)
        for dtype in smry.drop(["REAL", "DATE"], axis=1).dtypes
    )
    smry = emodel.load_smry(
        column_keys=["F[OGW]P?", "WWCT:OP*", "FOIP"], time_index="yearly"
    )
    assert set(smry.columns) == set(
        [
            "REAL",
            "DATE",
            "FGPP",
            "FGPR",
            "FGPT",
            "FOPP",
            "FOPR",
            "FOPT",
            "FWPP",
            "FWPR",
            "FWPT",
            "WWCT:OP_1",
            "WWCT:OP_2",
            "WWCT:OP_3",
            "WWCT:OP_4",
            "WWCT:OP_5",
            "FOIP",
        ]
    )


@pytest.mark.usefixtures("app")
def test_smry_meta(testdata_folder):
    emodel = EnsembleModel(
        ensemble_name="iter-0",
        ensemble_path=Path(testdata_folder)
        / "reek_history_match"
        / "realization-*"
        / "iter-0",
    )
    smeta = emodel.load_smry_meta()
    assert set(smeta.columns) == set(
        ["unit", "is_total", "is_rate", "is_historical", "keyword", "wgname", "get_num"]
    )
    assert len(smeta) == 473
    assert "FOPT" in smeta.index


@pytest.mark.usefixtures("app")
def test_parameter_loading(testdata_folder):
    emodel = EnsembleModel(
        ensemble_name="iter-0",
        ensemble_path=Path(testdata_folder)
        / "reek_history_match"
        / "realization-*"
        / "iter-0",
    )
    parameters = emodel.load_parameters()
    assert "REAL" in parameters.columns
    assert parameters["REAL"].dtype == np.dtype("int64")
    assert len(parameters.columns) == 27


@pytest.mark.usefixtures("app")
def test_load_csv(testdata_folder):
    emodel = EnsembleModel(
        ensemble_name="iter-0",
        ensemble_path=Path(testdata_folder)
        / "reek_history_match"
        / "realization-*"
        / "iter-0",
    )
    dframe = emodel.load_csv(Path("share") / "results" / "tables" / "rft.csv")
    assert "REAL" in dframe.columns
    assert dframe["REAL"].dtype == np.dtype("int64")
    assert len(dframe.columns) == 14


@pytest.mark.usefixtures("app")
def test_webviz_store(testdata_folder):
    emodel = EnsembleModel(
        ensemble_name="iter-0",
        ensemble_path=Path(testdata_folder)
        / "reek_history_match"
        / "realization-*"
        / "iter-0",
    )
    emodel.load_parameters()
    assert len(emodel.webviz_store) == 1
    emodel.load_smry()
    assert len(emodel.webviz_store) == 2
    emodel.load_smry(column_keys=["FOIP"])
    assert len(emodel.webviz_store) == 3
    emodel.load_smry(time_index="raw")
    assert len(emodel.webviz_store) == 4
    emodel.load_smry_meta()
    assert len(emodel.webviz_store) == 5
    emodel.load_smry_meta(column_keys=["R*", "GW?T*"])
    assert len(emodel.webviz_store) == 6
    emodel.load_csv(Path("share") / "results" / "tables" / "rft.csv")
    assert len(emodel.webviz_store) == 7
