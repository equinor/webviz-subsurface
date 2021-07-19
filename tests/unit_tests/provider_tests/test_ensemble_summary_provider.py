from typing import Dict
from pathlib import Path
import datetime

from webviz_subsurface._providers.ensemble_summary_provider_factory import (
    EnsembleSummaryProviderFactory,
)
from webviz_subsurface._providers.ensemble_summary_provider_factory import BackingType

BACKING_TYPE_TO_TEST: BackingType = BackingType.ARROW

# -------------------------------------------------------------------------
def test_create_from_aggregated_csv(testdata_folder: Path, tmp_path: Path) -> None:

    factory = EnsembleSummaryProviderFactory(tmp_path, BACKING_TYPE_TO_TEST)

    csv_filename = testdata_folder / "aggregated_data" / "smry_hm.csv"
    pset = factory.create_provider_set_from_aggregated_csv_file(csv_filename)
    assert pset.ensemble_names() == ["iter-0", "iter-3"]

    p = pset.provider("iter-0")
    vecnames = p.vector_names()
    assert len(vecnames) == 473
    assert vecnames[0] == "BPR:15,28,1"
    assert vecnames[472] == "YEARS"

    realizations = p.realizations()
    assert len(realizations) == 10

    vecdf = p.get_vectors_df(["FOPR"])
    assert vecdf.shape == (380, 3)
    assert vecdf.columns.tolist() == ["DATE", "REAL", "FOPR"]
    assert vecdf["REAL"].nunique() == 10
    sampleddate = vecdf["DATE"][0]
    assert isinstance(sampleddate, datetime.datetime)

    vecdf = p.get_vectors_df(["FOPR"], [1])
    assert vecdf.shape == (38, 3)
    assert vecdf.columns.tolist() == ["DATE", "REAL", "FOPR"]
    assert vecdf["REAL"].nunique() == 1


# -------------------------------------------------------------------------
def test_create_from_per_realization_csv_file(
    testdata_folder: Path, tmp_path: Path
) -> None:

    factory = EnsembleSummaryProviderFactory(tmp_path, BACKING_TYPE_TO_TEST)

    ensembles: Dict[str, str] = {
        "iter-0": str(testdata_folder / "reek_history_match/realization-*/iter-0"),
        "iter-1": str(testdata_folder / "reek_history_match/realization-*/iter-1"),
        "iter-2": str(testdata_folder / "reek_history_match/realization-*/iter-2"),
        "iter-3": str(testdata_folder / "reek_history_match/realization-*/iter-3"),
    }
    csvfile = "share/results/tables/unsmry--monthly.csv"

    pset = factory.create_provider_set_from_per_realization_csv_file(ensembles, csvfile)
    assert pset.ensemble_names() == ["iter-0", "iter-1", "iter-2", "iter-3"]

    p = pset.provider("iter-0")
    vecnames = p.vector_names()
    assert len(vecnames) == 473
    assert vecnames[0] == "BPR:15,28,1"
    assert vecnames[472] == "YEARS"

    realizations = p.realizations()
    assert len(realizations) == 10

    vecdf = p.get_vectors_df(["FOPR"])
    assert vecdf.shape == (380, 3)
    assert vecdf.columns.tolist() == ["DATE", "REAL", "FOPR"]
    assert vecdf["REAL"].nunique() == 10
    sampleddate = vecdf["DATE"][0]
    assert isinstance(sampleddate, datetime.datetime)

    vecdf = p.get_vectors_df(["FOPR"], [1])
    assert vecdf.shape == (38, 3)
    assert vecdf.columns.tolist() == ["DATE", "REAL", "FOPR"]
    assert vecdf["REAL"].nunique() == 1


# -------------------------------------------------------------------------
def test_create_from_ensemble_smry_fmu(testdata_folder: Path, tmp_path: Path) -> None:

    factory = EnsembleSummaryProviderFactory(tmp_path, BACKING_TYPE_TO_TEST)

    ensembles: Dict[str, str] = {
        "iter-0": str(testdata_folder / "reek_history_match/realization-*/iter-0"),
        "iter-1": str(testdata_folder / "reek_history_match/realization-*/iter-1"),
        "iter-2": str(testdata_folder / "reek_history_match/realization-*/iter-2"),
        "iter-3": str(testdata_folder / "reek_history_match/realization-*/iter-3"),
    }

    pset = factory.create_provider_set_from_ensemble_smry_fmu(ensembles, "monthly")
    assert pset.ensemble_names() == ["iter-0", "iter-1", "iter-2", "iter-3"]

    p = pset.provider("iter-0")
    vecnames = p.vector_names()
    assert len(vecnames) == 473
    assert vecnames[0] == "BPR:15,28,1"
    assert vecnames[472] == "YEARS"

    realizations = p.realizations()
    assert len(realizations) == 10

    vecdf = p.get_vectors_df(["FOPR"])
    assert vecdf.shape == (380, 3)
    assert vecdf.columns.tolist() == ["DATE", "REAL", "FOPR"]
    assert vecdf["REAL"].nunique() == 10
    sampleddate = vecdf["DATE"][0]
    assert isinstance(sampleddate, datetime.datetime)

    vecdf = p.get_vectors_df(["FOPR"], [1])
    assert vecdf.shape == (38, 3)
    assert vecdf.columns.tolist() == ["DATE", "REAL", "FOPR"]
    assert vecdf["REAL"].nunique() == 1
