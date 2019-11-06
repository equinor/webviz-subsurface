import pandas as pd
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

try:
    from fmu.ensemble import EnsembleSet
except ImportError:  # fmu.ensemble is an optional dependency, e.g.
    pass  # for a portable webviz instance, it is never used.

from ._history_match import scratch_ensemble


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def load_ensemble_set(
    ensemble_paths: tuple,
    ensemble_set_name: str = "EnsembleSet",
    unsmry_files: tuple = None,
):

    ensembles = []
    if unsmry_files is not None:
        unsmry_files = dict(unsmry_files)

    for ens_name, ens_path in ensemble_paths:
        if unsmry_files is not None and ens_name in unsmry_files:
            scratch_ens = scratch_ensemble(ens_name, ens_path, autodiscovery=False)
            scratch_ens.find_files(unsmry_files[ens_name])
            ensembles.append(scratch_ens)
        else:
            ensembles.append(scratch_ensemble(ens_name, ens_path))

    ensset = EnsembleSet(ensemble_set_name, ensembles)

    return ensset


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def get_time_series_statistics(
    ensemble_paths: tuple,
    time_index: str,
    column_keys: tuple,
    unsmry_files: tuple = None,
) -> pd.DataFrame:

    column_keys = list(column_keys) if isinstance(column_keys, (list, tuple)) else None

    # Note: to be replaced by ensset.get_smry_stats()
    # when function is available.
    # See:
    # https://github.com/equinor/fmu-ensemble/pull/19
    smry_stats = []
    if unsmry_files is not None:
        unsmry_files = dict(unsmry_files)

    for ens_name, ens_path in ensemble_paths:
        if unsmry_files is not None and ens_name in unsmry_files:
            ens = scratch_ensemble(ens_name, ens_path, autodiscovery=False)
            ens.find_files(unsmry_files[ens_name])
            ens_smry_stats = ens.get_smry_stats(
                time_index=time_index, column_keys=column_keys
            )
        else:
            ens_smry_stats = scratch_ensemble(ens_name, ens_path).get_smry_stats(
                time_index=time_index, column_keys=column_keys
            )
        ens_smry_stats["ENSEMBLE"] = ens_name
        smry_stats.append(ens_smry_stats)

    return pd.concat(smry_stats)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def get_time_series_data(
    ensemble_paths: tuple,
    time_index: str,
    column_keys: tuple,
    unsmry_files: tuple = None,
    ensemble_set_name: str = "EnsembleSet",
) -> pd.DataFrame:

    column_keys = list(column_keys) if isinstance(column_keys, (list, tuple)) else None

    ensset = load_ensemble_set(
        ensemble_paths=ensemble_paths,
        ensemble_set_name=ensemble_set_name,
        unsmry_files=unsmry_files,
    )

    return ensset.get_smry(time_index=time_index, column_keys=column_keys)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def get_time_series_delta_ens(
    ensemble_paths: tuple,
    time_index: str,
    column_keys: tuple,
    base_ensembles: tuple,
    delta_ensembles: tuple,
    unsmry_files: tuple = None,
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
        ensemble_paths=ensemble_paths,
        ensemble_set_name=ensemble_set_name,
        unsmry_files=unsmry_files,
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


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def get_time_series_delta_ens_stats(
    ensemble_paths: tuple,
    time_index: str,
    column_keys: tuple,
    base_ensembles: tuple,
    delta_ensembles: tuple,
    unsmry_files: tuple = None,
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
        ensemble_paths=ensemble_paths,
        ensemble_set_name=ensemble_set_name,
        unsmry_files=unsmry_files,
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
