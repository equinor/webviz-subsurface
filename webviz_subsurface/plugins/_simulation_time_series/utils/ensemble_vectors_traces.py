from typing import Dict, List

import pandas as pd

from .plotting import (
    create_vector_realization_traces,
    create_vector_statistics_traces,
    create_vector_fanchart_traces,
)
from .statistics import create_vectors_statistics_df
from ..types import FanchartOptions, StatisticsOptions

from ...._utils.simulation_timeseries import (
    render_hovertemplate,
)


def create_ensemble_vectors_statistics_traces(
    ensemble_vectors_df: pd.DataFrame,
    color: str,
    vector_line_shapes: Dict[str, str],
    ensemble: str,
    interval: str,
    statistics_options: List[StatisticsOptions],
) -> Dict[str, List[dict]]:
    """Get statistics traces for ensemble vectors from ensemble vectors DataFrame

    `Input:`
     * ensemble_vectors_df - DataFrame with columns ["DATE", "REAL", vector1, ..., vectorN]

     `Output:`
     * dict - Vector name as key and List of corresponding statistics traces as value
    """
    # Dictionary with vector name as key and list of ensemble traces as value
    vector_traces_dict: Dict[str, List[dict]] = {}
    vectors_statistics_df = create_vectors_statistics_df(ensemble_vectors_df)
    ensemble_vectors = [
        col
        for col in ensemble_vectors_df.columns.tolist()
        if col not in ["DATE", "REAL"]
    ]

    for vector in set(ensemble_vectors):
        vector_traces_dict[vector] = create_vector_statistics_traces(
            ensemble_vector_statistic_df=vectors_statistics_df,
            vector=vector,
            color=color,
            legend_group=ensemble,
            line_shape=vector_line_shapes[vector],
            hovertemplate=render_hovertemplate(vector=vector, interval=interval),
            statistics_options=statistics_options,
            show_legend=False,
        )

    # Add legend for ensemble - utilize one trace dict
    for traces in vector_traces_dict.values():
        if len(traces) > 0:
            trace: dict = traces[0]
            trace["showlegend"] = True
            break

    return vector_traces_dict


def create_ensemble_vectors_fanchart_traces(
    ensemble_vectors_df: pd.DataFrame,
    color: str,
    vector_line_shapes: Dict[str, str],
    ensemble: str,
    interval: str,
    fanchart_options: List[FanchartOptions],
) -> Dict[str, List[dict]]:
    """Get fanchart traces for ensemble vectors from ensemble vectors DataFrame

    `Input:`
     * ensemble_vectors_df - DataFrame with columns ["DATE", "REAL", vector1, ..., vectorN]
     * fanchart_options - Optional fanchart statistics to include

     `Output:`
     * dict - Vector name as key and List of corresponding fanchart traces as value
    """
    # Dictionary with vector name as key and list of ensemble traces as value
    vector_traces_dict: Dict[str, List[dict]] = {}
    vectors_statistics_df = create_vectors_statistics_df(ensemble_vectors_df)
    ensemble_vectors = [
        col
        for col in ensemble_vectors_df.columns.tolist()
        if col not in ["DATE", "REAL"]
    ]

    for vector in set(ensemble_vectors):
        vector_traces_dict[vector] = create_vector_fanchart_traces(
            ensemble_vector_statistic_df=vectors_statistics_df,
            vector=vector,
            color=color,
            legend_group=ensemble,
            line_shape=vector_line_shapes[vector],
            fanchart_options=fanchart_options,
            show_legend=False,
            hovertemplate=render_hovertemplate(vector=vector, interval=interval),
        )

    # Set show legend on last trace in last vector trace list (mean will be last
    # trace with solid line)
    if len(vector_traces_dict) > 0 and len(list(vector_traces_dict.values())[-1]) > 0:
        trace = list(vector_traces_dict.values())[-1][-1]
        trace["showlegend"] = True

    return vector_traces_dict


def create_ensemble_vectors_realizations_traces(
    ensemble_vectors_df: pd.DataFrame,
    color: str,
    ensemble: str,
    vector_line_shapes: Dict[str, str],
    interval: str,
) -> Dict[str, List[dict]]:
    """Get realization traces for ensemble vectors from ensemble vectors DataFrame

    `Input:`
     * ensemble_vectors_df - DataFrame with columns ["DATE", "REAL", vector1, ..., vectorN]

     `Output:`
     * dict - Vector name as key and List of corresponding realization traces as value
    """
    # Dictionary with vector name as key and list of ensemble traces as value
    vector_traces_dict: Dict[str, List[dict]] = {}
    ensemble_vectors = [
        col
        for col in ensemble_vectors_df.columns.tolist()
        if col not in ["DATE", "REAL"]
    ]

    for vector in set(ensemble_vectors):
        vector_traces_dict[vector] = create_vector_realization_traces(
            ensemble_vectors_df=ensemble_vectors_df,
            vector=vector,
            ensemble=ensemble,
            color=color,
            line_shape=vector_line_shapes[vector],
            hovertemplate=render_hovertemplate(vector, interval),
            show_legend=False,
        )

    # Add legend for ensemble - utilize one trace dict
    for traces in vector_traces_dict.values():
        if len(traces) > 0:
            trace: dict = traces[0]
            trace["showlegend"] = True
            break
    return vector_traces_dict
