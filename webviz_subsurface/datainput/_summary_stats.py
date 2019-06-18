import pandas as pd
from webviz_config.common_cache import cache
from webviz_config.webviz_store import webvizstore
from ..datainput import scratch_ensemble


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def get_summary_data(ensemble_paths: tuple, sampling: str,
                     column_keys: tuple) -> pd.DataFrame:
    """ Loops over given ensemble paths, extracts smry-data and concates them
    into one big df. An additional column ENSEMBLE is added for each
    ens-path to seperate the ensambles.
    column_keys is converted to list as list-type is needed in
    .get_smry_stats()"""

    column_keys = list(column_keys) if isinstance(
        column_keys, (list, tuple)) else None

    smry_data = []
    for ens, ens_path in ensemble_paths:
        ens_smry_data = scratch_ensemble(
            ens, ens_path).get_smry(
                time_index=sampling, column_keys=column_keys)
        ens_smry_data['ENSEMBLE'] = ens
        smry_data.append(ens_smry_data)
    return pd.concat(smry_data)


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def get_summary_stats(ensemble_paths: tuple, sampling: str,
                      column_keys: tuple) -> pd.DataFrame:
    """ Loops over given ensemble paths, extracts smry-data and concates them
    into one big df. An additional column ENSEMBLE is added for each
    ens-path to seperate the ensambles.
    column_keys is converted to list as list-type is needed in
    .get_smry_stats()"""

    column_keys = list(column_keys) if isinstance(
        column_keys, (list, tuple)) else None

    smry_stats = []
    for ens, ens_path in ensemble_paths:
        ens_smry_stats = scratch_ensemble(
            ens, ens_path).get_smry_stats(
                time_index=sampling, column_keys=column_keys)
        ens_smry_stats['ENSEMBLE'] = ens
        smry_stats.append(ens_smry_stats)

    return pd.concat(smry_stats)
