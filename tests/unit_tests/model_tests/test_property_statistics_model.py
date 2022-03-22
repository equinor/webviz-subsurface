from pathlib import Path

import pandas as pd
from webviz_config.themes import default_theme

from webviz_subsurface.plugins._property_statistics.models.property_statistics_model import (
    PropertyStatisticsModel,
)

from webviz_subsurface._providers import EnsembleTableProviderFactory


def get_provider(testdata_folder: Path) -> pd.DataFrame:
    table_provider = EnsembleTableProviderFactory.instance()
    return table_provider.create_provider_set_from_aggregated_csv_file(
        testdata_folder
        / "reek_test_data"
        / "aggregated_data"
        / "property_statistics.csv"
    )


def test_init(testdata_folder: Path) -> None:

    provider = get_provider(testdata_folder)
    model = PropertyStatisticsModel(provider=provider, theme=default_theme)
    assert set(model.dataframe.columns) == set(
        [
            "PROPERTY",
            "ZONE",
            "REGION",
            "FACIES",
            "Avg",
            "Avg_Weighted",
            "Max",
            "Min",
            "P10",
            "P90",
            "Stddev",
            "SOURCE",
            "ID",
            "REAL",
            "ENSEMBLE",
            "label",
        ]
    )
