from pathlib import Path

import pandas as pd
from webviz_config.themes import default_theme

from webviz_subsurface.plugins._property_statistics.models.property_statistics_model import (
    PropertyStatisticsModel,
)


def get_data_df(testdata_folder: Path) -> pd.DataFrame:

    return pd.read_csv(
        testdata_folder
        / "reek_test_data"
        / "aggregated_data"
        / "property_statistics.csv"
    )


def test_init(testdata_folder: Path) -> None:
    data_df = get_data_df(testdata_folder)
    model = PropertyStatisticsModel(dataframe=data_df, theme=default_theme)
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
