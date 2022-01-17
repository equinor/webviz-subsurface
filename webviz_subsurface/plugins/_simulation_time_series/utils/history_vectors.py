from typing import Dict, List, Optional

import pandas as pd

from webviz_subsurface._abbreviations.reservoir_simulation import historical_vector
from webviz_subsurface._providers import EnsembleSummaryProvider, Frequency


def create_history_vectors_df(
    provider: EnsembleSummaryProvider,
    vector_names: List[str],
    resampling_frequency: Optional[Frequency],
) -> pd.DataFrame:
    """Get dataframe with existing historical vector data for provided vectors.

    The returned dataframe contains columns with name of vector and corresponding historical
    data

    `Input:`
    * ensemble: str - Ensemble name
    * vector_names: List[str] - list of vectors to get historical data for
    [vector1, ... , vectorN]

    `Output:`
    * dataframe with non-historical vector names in columns and their historical data in rows.
    `Columns` in dataframe: ["DATE", "REAL", vector1, ..., vectorN]

    ---------------------
    `NOTE:`
    * Raise ValueError if vector does not exist for ensemble
    * If historical data does not exist for provided vector, vector is excluded from
    the returned dataframe.
    * Column names are not the historical vector name, but the original vector name,
    i.e. `WOPTH:OP_1` data is placed in colum with name `WOPT:OP_1`
    """
    if len(vector_names) < 1:
        raise ValueError("Empty list of vector names!")

    provider_vectors = provider.vector_names()
    resampling_frequency = (
        resampling_frequency if provider.supports_resampling() else None
    )

    # Verify for provider
    for elm in vector_names:
        if elm not in provider_vectors:
            raise ValueError(f'Vector "{elm}" not present among vectors for provider')

    # Dict with historical vector name as key, and non-historical vector name as value
    historical_vector_and_vector_name_dict: Dict[str, str] = {}
    for vector in vector_names:
        # TODO: Create new historical_vector according to new provider metadata?
        historical_vector_name = historical_vector(vector=vector, smry_meta=None)
        if historical_vector_name and historical_vector_name in provider.vector_names():
            historical_vector_and_vector_name_dict[historical_vector_name] = vector

    # Get lowest valid realization number
    realization = min(provider.realizations(), default=None)
    if not historical_vector_and_vector_name_dict or realization is None:
        return pd.DataFrame()

    historical_vector_names = list(historical_vector_and_vector_name_dict.keys())
    historical_vectors_df = provider.get_vectors_df(
        historical_vector_names, resampling_frequency, realizations=[realization]
    )
    return historical_vectors_df.rename(columns=historical_vector_and_vector_name_dict)
