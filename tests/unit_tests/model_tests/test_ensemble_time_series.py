from typing import Dict
from pathlib import Path

from webviz_subsurface._models.ensemble_time_series_factory import (
    EnsembleTimeSeriesFactory,
)
from webviz_subsurface._models.ensemble_time_series_factory import BackingType

BACKING_TYPE: BackingType = BackingType.ARROW


# -------------------------------------------------------------------------
def test_create_from_aggregated_csv(testdata_folder: Path, tmp_path: Path) -> None:

    factory = EnsembleTimeSeriesFactory(tmp_path, BACKING_TYPE)

    csv_filename = testdata_folder / "aggregated_data" / "smry_hm.csv"
    tsset = factory.create_time_series_set_from_aggregated_csv_file(csv_filename)
    assert tsset.ensemble_names() == ["iter-0", "iter-3"]

    ts = tsset.ensemble("iter-0")
    vecnames = ts.vector_names()
    assert len(vecnames) == 473
    assert vecnames[0] == "BPR:15,28,1"
    assert vecnames[472] == "YEARS"

    realizations = ts.realizations()
    assert len(realizations) == 10

    vecdf = ts.get_vectors_df(["FOPR"])
    assert vecdf.shape == (380, 3)
    assert vecdf.columns.tolist() == ["DATE", "REAL", "FOPR"]
    assert vecdf["REAL"].nunique() == 10

    vecdf = ts.get_vectors_df(["FOPR"], [1])
    assert vecdf.shape == (38, 3)
    assert vecdf.columns.tolist() == ["DATE", "REAL", "FOPR"]
    assert vecdf["REAL"].nunique() == 1


# -------------------------------------------------------------------------
def test_create_from_per_realization_csv_files(
    testdata_folder: Path, tmp_path: Path
) -> None:

    factory = EnsembleTimeSeriesFactory(tmp_path, BACKING_TYPE)

    ensembles: Dict[str, str] = {
        "iter-0": str(testdata_folder / "reek_history_match/realization-*/iter-0"),
        "iter-1": str(testdata_folder / "reek_history_match/realization-*/iter-1"),
        "iter-2": str(testdata_folder / "reek_history_match/realization-*/iter-2"),
        "iter-3": str(testdata_folder / "reek_history_match/realization-*/iter-3"),
    }
    csvfile = "share/results/tables/unsmry--monthly.csv"

    tsset = factory.create_time_series_set_from_per_realization_csv_files(
        ensembles, csvfile
    )
    assert tsset.ensemble_names() == ["iter-0", "iter-1", "iter-2", "iter-3"]

    ts = tsset.ensemble("iter-0")
    vecnames = ts.vector_names()
    assert len(vecnames) == 473
    assert vecnames[0] == "BPR:15,28,1"
    assert vecnames[472] == "YEARS"

    realizations = ts.realizations()
    assert len(realizations) == 10

    vecdf = ts.get_vectors_df(["FOPR"])
    assert vecdf.shape == (380, 3)
    assert vecdf.columns.tolist() == ["DATE", "REAL", "FOPR"]
    assert vecdf["REAL"].nunique() == 10

    vecdf = ts.get_vectors_df(["FOPR"], [1])
    assert vecdf.shape == (38, 3)
    assert vecdf.columns.tolist() == ["DATE", "REAL", "FOPR"]
    assert vecdf["REAL"].nunique() == 1


# -------------------------------------------------------------------------
def test_create_from_ensemble_smry(testdata_folder: Path, tmp_path: Path) -> None:

    factory = EnsembleTimeSeriesFactory(tmp_path, BACKING_TYPE)

    ensembles: Dict[str, str] = {
        "iter-0": str(testdata_folder / "reek_history_match/realization-*/iter-0"),
        "iter-1": str(testdata_folder / "reek_history_match/realization-*/iter-1"),
        "iter-2": str(testdata_folder / "reek_history_match/realization-*/iter-2"),
        "iter-3": str(testdata_folder / "reek_history_match/realization-*/iter-3"),
    }

    tsset = factory.create_time_series_set_from_ensemble_smry(ensembles, "monthly")
    assert tsset.ensemble_names() == ["iter-0", "iter-1", "iter-2", "iter-3"]

    ts = tsset.ensemble("iter-0")
    vecnames = ts.vector_names()
    assert len(vecnames) == 473
    assert vecnames[0] == "BPR:15,28,1"
    assert vecnames[472] == "YEARS"

    realizations = ts.realizations()
    assert len(realizations) == 10

    vecdf = ts.get_vectors_df(["FOPR"])
    assert vecdf.shape == (380, 3)
    assert vecdf.columns.tolist() == ["DATE", "REAL", "FOPR"]
    assert vecdf["REAL"].nunique() == 10

    vecdf = ts.get_vectors_df(["FOPR"], [1])
    assert vecdf.shape == (38, 3)
    assert vecdf.columns.tolist() == ["DATE", "REAL", "FOPR"]
    assert vecdf["REAL"].nunique() == 1
