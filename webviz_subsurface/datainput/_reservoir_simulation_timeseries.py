# -*- coding: utf-8 -*-
""" time-series data-input functions
    - Process ensemble-data (read, filter, compare)
    - Treated as ensembleset-object (independent of n-ensembles)
"""


try:
    from fmu.ensemble import EnsembleSet
except ImportError:  # fmu.ensemble is an optional dependency, e.g.
    pass  # for a portable webviz instance, it is never used.


import pandas as pd
from webviz_config.common_cache import cache
from webviz_config.webviz_store import webvizstore
from ..datainput import scratch_ensemble


@cache.memoize(timeout=cache.TIMEOUT)
def load_ensemble_set(ensemble_paths: tuple, ensemble_set_name: str = "EnsembleSet"):

    return EnsembleSet(
        ensemble_set_name,
        [scratch_ensemble(ens_name, ens_path) for ens_name, ens_path in ensemble_paths],
    )


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def get_time_series_statistics(
    ensemble_paths: tuple, time_index: str, column_keys: tuple
) -> pd.DataFrame:

    column_keys = list(column_keys) if isinstance(column_keys, (list, tuple)) else None

    # Note: to be replaced by ensset.get_smry_stats()
    # when function is available.
    # See:
    # https://github.com/equinor/fmu-ensemble/pull/19
    smry_stats = []
    for ens, ens_path in ensemble_paths:
        ens_smry_stats = scratch_ensemble(ens, ens_path).get_smry_stats(
            time_index=time_index, column_keys=column_keys
        )
        ens_smry_stats["ENSEMBLE"] = ens
        smry_stats.append(ens_smry_stats)

    return pd.concat(smry_stats)


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def get_time_series_data(
    ensemble_paths: tuple,
    time_index: str,
    column_keys: tuple,
    ensemble_set_name: str = "EnsembleSet",
) -> pd.DataFrame:

    column_keys = list(column_keys) if isinstance(column_keys, (list, tuple)) else None

    ensset = load_ensemble_set(
        ensemble_paths=ensemble_paths, ensemble_set_name=ensemble_set_name
    )

    return ensset.get_smry(time_index=time_index, column_keys=column_keys)


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def get_time_series_delta_ens(
    ensemble_paths: tuple,
    time_index: str,
    column_keys: tuple,
    base_ensembles: tuple,
    delta_ensembles: tuple,
    ensemble_set_name: str = "EnsembleSet",
) -> pd.DataFrame:
    """ Loads ensembleset (cached after first loaded), gets a list of
    ensemblenames and loops over possible combinations to be compared
    and gathers the resulting dataframes.
    Delta-Ens-Values can then be extracted from the get_time_series_delta_ens
    dataframe.
    """

    column_keys = list(column_keys) if isinstance(column_keys, (list, tuple)) else None

    ensset = load_ensemble_set(
        ensemble_paths=ensemble_paths, ensemble_set_name=ensemble_set_name
    )

    delta_ens_dfs = []
    for ens_i in base_ensembles:
        for ens_ii in delta_ensembles:
            fieldgain_df = (ensset[ens_i] - ensset[ens_ii]).get_smry(
                column_keys=column_keys, time_index=time_index
            )
            fieldgain_df["IROENS - REFENS"] = f"{ens_i} - {ens_ii}"
            delta_ens_dfs.append(fieldgain_df)

    return pd.concat(delta_ens_dfs)


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def get_time_series_delta_ens_stats(
    ensemble_paths: tuple,
    time_index: str,
    column_keys: tuple,
    base_ensembles: tuple,
    delta_ensembles: tuple,
    ensemble_set_name: str = "EnsembleSet",
) -> pd.DataFrame:
    """ Loads ensembleset (cached after first loaded), gets a list of
    ensemblenames and loops over possible combinations to be compared
    and gathers the resulting dataframes.
    Delta-Ens-Statistics can then be extracted from the
    get_time_series_delta_ens dataframe.
    """

    column_keys = list(column_keys) if isinstance(column_keys, (list, tuple)) else None

    ensset = load_ensemble_set(
        ensemble_paths=ensemble_paths, ensemble_set_name=ensemble_set_name
    )

    delta_ens_stats_dfs = []
    for ens_i in base_ensembles:
        for ens_ii in delta_ensembles:
            fieldgain_stats_df = (ensset[ens_i] - ensset[ens_ii]).get_smry_stats(
                column_keys=column_keys, time_index=time_index
            )
            fieldgain_stats_df["IROENS - REFENS"] = f"{ens_i} - {ens_ii}"
            delta_ens_stats_dfs.append(fieldgain_stats_df)

    return pd.concat(delta_ens_stats_dfs)
