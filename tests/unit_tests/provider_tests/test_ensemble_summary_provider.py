from pathlib import Path
import datetime
import os
from webviz_subsurface._providers.ensemble_summary_provider.ensemble_summary_provider import (
    Frequency,
)

import pandas as pd

from webviz_subsurface._providers import EnsembleSummaryProviderFactory


def _split_aggr_csv_into_per_real(aggr_csvfile: str, output_folder: str) -> None:
    df = pd.read_csv(aggr_csvfile)
    df = df[df["ENSEMBLE"] == "iter-0"]
    df = df.drop(columns="ENSEMBLE")

    for real in range(0, 10):
        real_df = df[df["REAL"] == real]
        real_df = real_df.drop(columns="REAL")
        os.makedirs(f"{output_folder}/realization-{real}/iter-0/", exist_ok=True)
        real_df.to_csv(
            f"{output_folder}/realization-{real}/iter-0/smry.csv", index=False
        )


def test_create_from_arrow_unsmry_lazy(testdata_folder: Path, tmp_path: Path) -> None:

    factory = EnsembleSummaryProviderFactory(tmp_path)

    ensemble_path = testdata_folder / "01_drogon_ahm/realization-*/iter-0"
    provider = factory.create_from_arrow_unsmry_lazy(str(ensemble_path))


def test_create_from_arrow_unsmry_presampled_monthly(
    testdata_folder: Path, tmp_path: Path
) -> None:

    factory = EnsembleSummaryProviderFactory(tmp_path)

    ensemble_path = testdata_folder / "01_drogon_ahm/realization-*/iter-0"
    provider = factory.create_from_arrow_unsmry_presampled(
        str(ensemble_path), Frequency.MONTHLY
    )


def test_create_from_per_realization_csv_file(
    testdata_folder: Path, tmp_path: Path
) -> None:

    _split_aggr_csv_into_per_real(
        testdata_folder / "reek_test_data/aggregated_data/smry.csv",
        tmp_path / "fake_data",
    )

    factory = EnsembleSummaryProviderFactory(tmp_path)

    ens_path = tmp_path / "fake_data/realization-*/iter-0"
    csvfile = "smry.csv"
    p = factory.create_from_per_realization_csv_file(str(ens_path), csvfile)

    vecnames = p.vector_names()
    assert len(vecnames) == 16
    assert vecnames[0] == "FGIP"
    assert vecnames[15] == "YEARS"

    realizations = p.realizations()
    assert len(realizations) == 10

    vecdf = p.get_vectors_df(["FOPR"], None)
    assert vecdf.shape == (380, 3)
    assert vecdf.columns.tolist() == ["DATE", "REAL", "FOPR"]
    assert vecdf["REAL"].nunique() == 10
    sampleddate = vecdf["DATE"][0]
    assert isinstance(sampleddate, datetime.datetime)

    vecdf = p.get_vectors_df(["FOPR"], None, [1])
    assert vecdf.shape == (38, 3)
    assert vecdf.columns.tolist() == ["DATE", "REAL", "FOPR"]
    assert vecdf["REAL"].nunique() == 1


def test_create_from_ensemble_csv(testdata_folder: Path, tmp_path: Path) -> None:

    factory = EnsembleSummaryProviderFactory(tmp_path)

    csv_filename = (
        testdata_folder / "reek_test_data" / "aggregated_data" / "smry_hm.csv"
    )
    p = factory.create_from_ensemble_csv_file(csv_filename, "iter-0")

    vecnames = p.vector_names()
    assert len(vecnames) == 473
    assert vecnames[0] == "BPR:15,28,1"
    assert vecnames[472] == "YEARS"

    realizations = p.realizations()
    assert len(realizations) == 10

    dates = p.dates(None)
    assert len(dates) == 38
    assert isinstance(dates[0], datetime.datetime)
    assert dates[0] == datetime.datetime.fromisoformat("2000-01-01")
    assert dates[-1] == datetime.datetime.fromisoformat("2003-02-01")

    vecdf = p.get_vectors_df(["FOPR"], None)
    assert vecdf.shape == (380, 3)
    assert vecdf.columns.tolist() == ["DATE", "REAL", "FOPR"]
    assert vecdf["REAL"].nunique() == 10
    sampleddate = vecdf["DATE"][0]
    assert isinstance(sampleddate, datetime.datetime)

    vecdf = p.get_vectors_df(["FOPR"], None, [1])
    assert vecdf.shape == (38, 3)
    assert vecdf.columns.tolist() == ["DATE", "REAL", "FOPR"]
    assert vecdf["REAL"].nunique() == 1
