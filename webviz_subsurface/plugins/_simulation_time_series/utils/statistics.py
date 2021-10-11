from typing import List

import numpy as np
import pandas as pd


def create_vectors_statistics_df(ensemble_vectors_df: pd.DataFrame) -> pd.DataFrame:
    """
    Create vectors statistics dataframe for given vectors in an ensemble

    Calculate min, max, mean, p10,p90 and p50 for each vector in input dataframe

    `Returns:`
    * Dataframe with double column level:\n
      [            vector1,                        ... vectorN
        "DATE",    mean, min, max, p10, p90, p50   ... mean, min, max, p10, p90, p50]

    `Input:`
    * Dataframe with columns: ["DATE", "REAL", vector1, ..., vectorN]

    TODO: Consider if vector names should be provided separately? vectors: List[str]
    """

    vectors: List[str] = list(set(ensemble_vectors_df.columns) ^ set(["DATE", "REAL"]))

    # Invert p10 and p90 due to oil industry convention.
    def p10(x: List[float]) -> List[float]:
        return np.nanpercentile(x, q=90)

    def p90(x: List[float]) -> List[float]:
        return np.nanpercentile(x, q=10)

    def p50(x: List[float]) -> List[float]:
        return np.nanpercentile(x, q=50)

    # Calculate statistics, ignoring NaNs
    # TODO: Verify if calculation is correct
    statistics_df: pd.DataFrame = (
        ensemble_vectors_df[["DATE"] + vectors]
        .groupby(["DATE"])
        .agg([np.nanmean, np.nanmin, np.nanmax, p10, p90, p50])
        .reset_index(level=["DATE"], col_level=1)
    )

    # Rename nanmin, nanmax and nanmean to min, max and mean.
    col_stat_label_map = {
        "nanmin": "min",
        "nanmax": "max",
        "nanmean": "mean",
        "p10": "high_p10",
        "p90": "low_p90",
        "p50": "p50",
    }
    statistics_df.rename(columns=col_stat_label_map, level=1, inplace=True)

    return statistics_df
