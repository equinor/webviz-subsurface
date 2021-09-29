from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from webviz_subsurface._providers import (
    EnsembleTableProvider,
    EnsembleTableProviderFactory,
)
from webviz_subsurface._providers.ensemble_table_provider_factory import BackingType
from webviz_subsurface._providers.ensemble_table_provider_impl_arrow import (
    EnsembleTableProviderImplArrow,
)
from webviz_subsurface._providers.ensemble_table_provider_impl_inmem_parquet import (
    EnsembleTableProviderImplInMemParquet,
)

BACKING_TYPE_TO_TEST: BackingType = BackingType.ARROW


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

    use_arrow_implementation = True

    provider: Optional[EnsembleTableProvider]
    if use_arrow_implementation:
        EnsembleTableProviderImplArrow.write_backing_store_from_ensemble_dataframe(
            storage_dir, "dummy_key", input_df
        )
        provider = EnsembleTableProviderImplArrow.from_backing_store(
            storage_dir, "dummy_key"
        )
    else:
        EnsembleTableProviderImplInMemParquet.write_backing_store_from_ensemble_dataframe(
            storage_dir, "dummy_key", input_df
        )
        provider = EnsembleTableProviderImplInMemParquet.from_backing_store(
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


def test_create_from_aggregated_csv_file_smry_csv(
    testdata_folder: Path, tmp_path: Path
) -> None:
    factory = EnsembleTableProviderFactory(
        tmp_path, backing_type=BACKING_TYPE_TO_TEST, allow_storage_writes=True
    )
    providerset = factory.create_provider_set_from_aggregated_csv_file(
        testdata_folder / "reek_test_data" / "aggregated_data" / "smry.csv"
    )

    assert providerset.ensemble_names() == ["iter-0"]
    provider = providerset.ensemble_provider("iter-0")

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


def test_create_from_aggregated_csv_file_smry_hm(
    testdata_folder: Path, tmp_path: Path
) -> None:
    factory = EnsembleTableProviderFactory(
        tmp_path, backing_type=BACKING_TYPE_TO_TEST, allow_storage_writes=True
    )
    providerset = factory.create_provider_set_from_aggregated_csv_file(
        testdata_folder / "reek_test_data" / "aggregated_data" / "smry_hm.csv"
    )

    assert providerset.ensemble_names() == ["iter-0", "iter-3"]
    provider = providerset.ensemble_provider("iter-0")

    assert len(provider.column_names()) == 474
    assert provider.column_names()[0] == "DATE"
    assert provider.column_names()[1] == "BPR:15,28,1"
    assert provider.column_names()[473] == "YEARS"

    assert len(provider.realizations()) == 10

    valdf = provider.get_column_data(["DATE"])
    assert len(valdf.columns) == 2
    assert valdf.columns[0] == "REAL"
    assert valdf.columns[1] == "DATE"
    assert valdf["REAL"].nunique() == 10


def test_create_from_per_realization_csv_file(
    testdata_folder: Path, tmp_path: Path
) -> None:

    ensembles: Dict[str, str] = {
        "iter-0": str(testdata_folder / "01_drogon_ahm/realization-*/iter-0"),
        "iter-3": str(testdata_folder / "01_drogon_ahm/realization-*/iter-3"),
    }

    csvfile = "share/results/tables/rft.csv"

    factory = EnsembleTableProviderFactory(
        tmp_path, backing_type=BACKING_TYPE_TO_TEST, allow_storage_writes=True
    )
    providerset = factory.create_provider_set_from_per_realization_csv_file(
        ensembles, csvfile
    )

    assert providerset.ensemble_names() == ["iter-0", "iter-3"]
    provider = providerset.ensemble_provider("iter-0")

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
