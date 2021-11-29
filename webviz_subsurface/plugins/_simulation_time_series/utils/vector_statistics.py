from typing import List

import numpy as np
import pandas as pd

from ..types import StatisticsOptions


def create_vectors_statistics_df(vectors_df: pd.DataFrame) -> pd.DataFrame:
    """
    Create vectors statistics dataframe for given vectors in columns of provided vectors dataframe

    Calculate min, max, mean, p10, p90 and p50 for each vector in dataframe column

    `Input:`
    * vectors_df: pd.DataFrame - Dataframe with vectors dataframe and columns:
        ["DATE", "REAL", vector1, ... , vectorN]

    # TODO: Verify returned dataframe index format
    `Returns:`
    * Dataframe with double column level:\n
      [ "DATE",     vector1,                        ... vectorN
                    MEAN, MIN, MAX, P10, P90, P50   ... MEAN, MIN, MAX, P10, P90, P50]
    """
    # TODO: Add verification of format and raise value error - i.e required columns and
    # "dimension" of vectors_statistics_df?

    vector_names: List[str] = list(set(vectors_df.columns) ^ set(["DATE", "REAL"]))

    # Invert p10 and p90 due to oil industry convention.
    def p10(x: List[float]) -> List[float]:
        return np.nanpercentile(x, q=90)

    def p90(x: List[float]) -> List[float]:
        return np.nanpercentile(x, q=10)

    def p50(x: List[float]) -> List[float]:
        return np.nanpercentile(x, q=50)

    statistics_df: pd.DataFrame = (
        vectors_df[["DATE"] + vector_names]
        .groupby(["DATE"])
        .agg([np.nanmean, np.nanmin, np.nanmax, p10, p90, p50])
        .reset_index(level=["DATE"], col_level=0)
    )

    # Rename nanmin, nanmax and nanmean to min, max and mean.
    col_stat_label_map = {
        "nanmin": StatisticsOptions.MIN,
        "nanmax": StatisticsOptions.MAX,
        "nanmean": StatisticsOptions.MEAN,
        "p10": StatisticsOptions.P10,
        "p90": StatisticsOptions.P90,
        "p50": StatisticsOptions.P50,
    }
    statistics_df.rename(columns=col_stat_label_map, level=1, inplace=True)

    return statistics_df
