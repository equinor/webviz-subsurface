from typing import List

import numpy as np
import pandas as pd

from webviz_subsurface._utils.dataframe_utils import (
    assert_date_column_is_datetime_object,
    make_date_column_datetime_object,
)

from ..types import StatisticsOptions


def create_vectors_statistics_df(vectors_df: pd.DataFrame) -> pd.DataFrame:
    """
    Create vectors statistics dataframe for given vectors in columns of provided vectors dataframe

    Calculate min, max, mean, p10, p90 and p50 for each vector in dataframe column

    `Input:`
    * vectors_df: pd.DataFrame - Dataframe with vectors dataframe and columns:
        ["DATE", "REAL", vector1, ... , vectorN]

    `Returns:`
    * Dataframe with double column level:\n
      [ "DATE",     vector1,                        ... vectorN
                    MEAN, MIN, MAX, P10, P90, P50   ... MEAN, MIN, MAX, P10, P90, P50]
    """
    assert_date_column_is_datetime_object(vectors_df)

    # Get vectors names, keep order
    columns_list = list(vectors_df.columns)
    vector_names = sorted(
        (set(columns_list) ^ set(["DATE", "REAL"])), key=columns_list.index
    )

    # If no rows of data:
    if not vectors_df.shape[0]:
        columns_tuples = [("DATE", "")]
        for vector in vector_names:
            columns_tuples.extend(
                [
                    (vector, StatisticsOptions.MEAN),
                    (vector, StatisticsOptions.MIN),
                    (vector, StatisticsOptions.MAX),
                    (vector, StatisticsOptions.P10),
                    (vector, StatisticsOptions.P90),
                    (vector, StatisticsOptions.P50),
                ]
            )
        return pd.DataFrame(columns=pd.MultiIndex.from_tuples(columns_tuples))

    # Invert p10 and p90 due to oil industry convention.
    def p10(x: List[float]) -> np.floating:
        return np.nanpercentile(x, q=90)

    def p90(x: List[float]) -> np.floating:
        return np.nanpercentile(x, q=10)

    def p50(x: List[float]) -> np.floating:
        return np.nanpercentile(x, q=50)

    statistics_df: pd.DataFrame = (
        vectors_df[["DATE"] + vector_names]
        .groupby(["DATE"])
        .agg([np.nanmean, np.nanmin, np.nanmax, p10, p90, p50])
        .reset_index(level=["DATE"], col_level=0)
    )

    # Rename columns to StatisticsOptions enum types for strongly typed format
    col_stat_label_map = {
        "nanmin": StatisticsOptions.MIN,
        "nanmax": StatisticsOptions.MAX,
        "nanmean": StatisticsOptions.MEAN,
        "p10": StatisticsOptions.P10,
        "p90": StatisticsOptions.P90,
        "p50": StatisticsOptions.P50,
    }
    statistics_df.rename(columns=col_stat_label_map, level=1, inplace=True)

    make_date_column_datetime_object(statistics_df)

    return statistics_df
