from typing import Dict, List, Optional

import pandas as pd

from webviz_subsurface._abbreviations.reservoir_simulation import historical_vector
from webviz_subsurface._providers import EnsembleSummaryProvider, Frequency

from .plotting import create_vector_history_trace


def create_historical_vectors_traces(
    provider: EnsembleSummaryProvider,
    resampling_frequency: Optional[Frequency],
    vectors: List[str],
    vector_line_shapes: Dict[str, str],
    show_legend: bool = False,
) -> Dict[str, dict]:
    """Get trace for historical vectors retreived from list of vectors and provider

    `Input:`
     * provider - Ensemble summary provider
     * vectors - list of vectors to get historical data for [vector1, ... , vectorN]

    `Output:`
     * dict - Vector name as key and history trace as value
    """
    historical_vectors_data_df: pd.DataFrame = _get_existing_historical_vectors_data_df(
        provider, resampling_frequency, vectors
    )

    vector_names = [
        col for col in historical_vectors_data_df.columns if col not in ["DATE", "REAL"]
    ]

    vector_trace_dict: Dict[str, dict] = {}
    for vector in vector_names:
        vector_trace_dict[vector] = create_vector_history_trace(
            historical_vectors_data_df,
            vector,
            line_shape=vector_line_shapes[vector],
            show_legend=show_legend,
        )
    return vector_trace_dict


def _get_existing_historical_vectors_data_df(
    provider: EnsembleSummaryProvider,
    resampling_frequency: Optional[Frequency],
    vectors: List[str],
) -> pd.DataFrame:
    """Get dataframe with existing historical vector data for provided vectors.

    The returned dataframe contains columns with name of vector and corresponding historical data

    `Input:`
     * provider - Ensemble summary provider
     * vectors - list of vectors to get historical data for [vector1, ... , vectorN]

    `Output:`
     * dataframe with non-historical vector names in columns and their historical data in rows.
    `Columns` in dataframe: ["DATE", "REAL", vector1, ..., vectorN]

    ---------------------
    `NOTE:`
    * If historical data does not exist for provided vector, vector is excluded from
    the returned dataframe.
    * Column names are not the historical vector name, but the original vector name,
    i.e. `WOPTH:OP_1` data is placed in colum with name `WOPT:OP_1`
    """
    if len(vectors) <= 0:
        return pd.DataFrame()

    # Filter vectors for provider
    vectors_filtered = [vec for vec in vectors if vec in provider.vector_names()]

    # Dict with historical vector name as key, and non-historical vector name as value
    historical_vector_and_vector_name_dict: Dict[str, str] = {}
    for vector in vectors_filtered:
        historical_vector_name = historical_vector(vector=vector, smry_meta=None)
        if historical_vector_name and historical_vector_name in provider.vector_names():
            historical_vector_and_vector_name_dict[historical_vector_name] = vector

    if not historical_vector_and_vector_name_dict:
        return pd.DataFrame()

    historical_vector_names = list(historical_vector_and_vector_name_dict.keys())

    # TODO: Ensure realization no 0 is good enough
    historical_vectors_df = provider.get_vectors_df(
        historical_vector_names, resampling_frequency, realizations=[0]
    )
    return historical_vectors_df.rename(columns=historical_vector_and_vector_name_dict)
