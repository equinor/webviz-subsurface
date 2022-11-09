from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from webviz_subsurface._providers import (
    ColumnMetadata,
    EnsembleTableProvider,
    EnsembleTableProviderFactory,
)
from webviz_subsurface._providers.ensemble_table_provider import (
    EnsembleTableProviderImplArrow,
)


def _create_synthetic_table_provider(
    storage_dir: Path,
) -> EnsembleTableProvider:
    # fmt: off
    input_data = [
        ["REAL",  "A",   "B",  "STR" ],
        [     0,  1.0,  11.0,   "aa" ],
        [     0,  2.0,  12.0,   "bb" ],
        [     0,  3.0,  13.0,   "cc" ],
        [     1,  4.0,  14.0,   "dd" ],
        [     1,  5.0,  15.0,   "ee" ],
        [     1,  6.0,  16.0,   "ff" ],
        [     1,  7.0,  17.0,   "gg" ],
    ]
    # fmt: on

    input_df = pd.DataFrame(input_data[1:], columns=input_data[0])

    provider: Optional[EnsembleTableProvider]

    EnsembleTableProviderImplArrow.write_backing_store_from_ensemble_dataframe(
        storage_dir, "dummy_key", input_df
    )
    provider = EnsembleTableProviderImplArrow.from_backing_store(
        storage_dir, "dummy_key"
    )

    if not provider:
        raise ValueError("Failed to create EnsembleTableProvider")

    return provider


def test_synthetic_get_column_data(testdata_folder: Path) -> None:
    model = _create_synthetic_table_provider(testdata_folder)
    assert model.column_names() == ["A", "B", "STR"]
    assert model.realizations() == [0, 1]

    df = model.get_column_data(["A"])
    assert df.shape == (7, 2)
    assert df.columns.tolist() == ["REAL", "A"]

    df = model.get_column_data(["STR"], [1])
    assert df.shape == (4, 2)
    assert df.columns.tolist() == ["REAL", "STR"]

    assert model.column_metadata("REAL") is None


def test_create_from_aggregated_csv_file_smry_csv(
    testdata_folder: Path, tmp_path: Path
) -> None:
    factory = EnsembleTableProviderFactory(tmp_path, allow_storage_writes=True)
    provider = factory.create_from_ensemble_csv_file(
        testdata_folder / "reek_test_data" / "aggregated_data" / "smry.csv"
    )

    assert len(provider.column_names()) == 17
    assert provider.column_names()[0] == "DATE"
    assert provider.column_names()[16] == "YEARS"

    assert len(provider.realizations()) == 40

    valdf = provider.get_column_data(["YEARS"])
    assert len(valdf.columns) == 2
    assert valdf.columns[0] == "REAL"
    assert valdf.columns[1] == "YEARS"
    assert valdf["REAL"].nunique() == 40

    valdf = provider.get_column_data(["YEARS"], [0, 39, 10])
    assert len(valdf.columns) == 2
    assert valdf.columns[0] == "REAL"
    assert valdf.columns[1] == "YEARS"
    assert valdf["REAL"].nunique() == 3

    # No metadata in csv files
    meta: Optional[ColumnMetadata] = provider.column_metadata("FOPR")
    assert meta is None


def test_create_from_per_realization_csv_file(
    testdata_folder: Path, tmp_path: Path
) -> None:

    factory = EnsembleTableProviderFactory(tmp_path, allow_storage_writes=True)
    provider = factory.create_from_per_realization_csv_file(
        str(testdata_folder / "01_drogon_ahm/realization-*/iter-0"),
        "share/results/tables/rft.csv",
    )

    all_column_names = provider.column_names()
    # print(all_column_names)
    assert len(all_column_names) == 13

    assert len(provider.realizations()) == 100

    valdf = provider.get_column_data(["CONIDX"], [2])
    assert valdf.shape == (218, 2)
    assert valdf.columns[0] == "REAL"
    assert valdf.columns[1] == "CONIDX"
    assert valdf["REAL"].unique() == [2]
    assert valdf["CONIDX"].nunique() == 24
    assert sorted(valdf["CONIDX"].unique()) == list(range(1, 25))

    # No metadata in csv files
    meta: Optional[ColumnMetadata] = provider.column_metadata("CONIDX")
    assert meta is None


def test_create_from_per_realization_arrow_file(
    testdata_folder: Path, tmp_path: Path
) -> None:

    factory = EnsembleTableProviderFactory(tmp_path, allow_storage_writes=True)
    provider = factory.create_from_per_realization_arrow_file(
        str(testdata_folder / "01_drogon_ahm/realization-*/iter-0"),
        "share/results/unsmry/*arrow",
    )

    valdf = provider.get_column_data(provider.column_names())
    assert valdf.shape[0] == 25284
    assert "FOPT" in valdf.columns
    assert valdf["REAL"].nunique() == 100

    # Test metadata
    meta: Optional[ColumnMetadata] = provider.column_metadata("FOPR")
    assert meta is not None
    assert meta.unit == "SM3/DAY"


def test_create_from_per_realization_parameter_file(
    testdata_folder: Path, tmp_path: Path
) -> None:

    factory = EnsembleTableProviderFactory(tmp_path, allow_storage_writes=True)
    provider = factory.create_from_per_realization_parameter_file(
        str(testdata_folder / "01_drogon_ahm/realization-*/iter-0")
    )

    valdf = provider.get_column_data(provider.column_names())
    assert "GLOBVAR:FAULT_SEAL_SCALING" in valdf.columns
    assert valdf["REAL"].nunique() == 100

    # No metadata in parameter files
    meta: Optional[ColumnMetadata] = provider.column_metadata(
        "GLOBVAR:FAULT_SEAL_SCALING"
    )
    assert meta is None


def test_create_provider_set_from_aggregated_csv_file(tmp_path: Path) -> None:
    """This tests importing a csv file with an ensemble column with multiple
    ensembles. It will return a dictionary of providers, one for each ensemble.
    """
    factory = EnsembleTableProviderFactory(tmp_path, allow_storage_writes=True)
    provider_set: Dict[
        str, EnsembleTableProvider
    ] = factory.create_provider_set_from_aggregated_csv_file("tests/data/volumes.csv")
    assert set(provider_set.keys()) == {"iter-0", "iter-1"}

    for _, provider in provider_set.items():
        valdf = provider.get_column_data(provider.column_names())
        print(valdf)
        print(provider.column_names())
        assert set(valdf["REAL"].unique()) == {0, 1}
        assert {
            "ZONE",
            "REGION",
            "BULK_OIL",
            "PORE_OIL",
            "HCPV_OIL",
            "STOIIP_OIL",
            "SOURCE",
        }.issubset(set(provider.column_names()))

        # No metadata in csv files
        meta: Optional[ColumnMetadata] = provider.column_metadata("ZONE")
        assert meta is None
