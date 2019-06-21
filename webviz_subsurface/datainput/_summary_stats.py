import pandas as pd
from webviz_config.common_cache import cache
from webviz_config.webviz_store import webvizstore
from fmu.ensemble import EnsembleSet
from ..datainput import scratch_ensemble

@cache.memoize(timeout=cache.TIMEOUT)
def load_ensemble_set(
        ensemble_paths: tuple,
        ensemble_set_name: str = 'EnsembleSet'):
    """Loops over given ensembles-path, loads them into memory and
    aggregates them into an EnsemlbeSet-obj. Main data on sumamry_stats
    container.
    Args:
        ensemble_paths: tuple = (name, path) of ensembles to load
        ensemle_set_name: str = name of enesemble-set
    Returns:
        EnsembleSet (collection of ensemble objects)
    """

    return EnsembleSet(
        ensemble_set_name,
        [scratch_ensemble(ens_name, ens_path)
         for ens_name, ens_path in ensemble_paths]
    )


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def get_summary_data(
        ensemble_paths: tuple,
        time_index: str,
        column_keys: tuple,
        ensemble_set_name: str = 'EnsembleSet'
    ) -> pd.DataFrame:
    """Retruns summary data of ensembleset. Operates on EnsemlbeSet-obj that
    is returned by load_ensemble_set() and cached after first call.
    Args:
        ensemble_paths: tuple = (name, path) of ensembles to load
        ensemle_set_name: str = name of enesemble-set
        time_index: str = timeseries steps
        column_keys: tuple = pre filtered vectors
    Retuns:
        summary-data-dataframe
    """

    column_keys = list(column_keys) if isinstance(
        column_keys, (list, tuple)) else None

    ensset = load_ensemble_set(
        ensemble_paths=ensemble_paths,
        ensemble_set_name=ensemble_set_name
    )

    return ensset.get_smry(
        time_index=time_index,
        column_keys=column_keys
    )


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def get_summary_stats(
        ensemble_paths: tuple,
        time_index: str,
        column_keys: tuple
    ) -> pd.DataFrame:
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
                time_index=time_index, column_keys=column_keys)
        ens_smry_stats['ENSEMBLE'] = ens
        smry_stats.append(ens_smry_stats)

    return pd.concat(smry_stats)


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def get_fieldgain(
        ensemble_paths: tuple,
        time_index: str,
        column_keys: tuple,
        iorens: str,
        refens: str,
        ensemble_set_name: str = 'EnsembleSet'
    ) -> pd.DataFrame:
    """Calulates differnces between two ensembles and retunrs a dataframe of
    delta-data. Operates on EnsemlbeSet-obj that is returned by
    load_ensemble_set() and cached after first call.
    Args:
        ensemble_paths: tuple = (name, path) of ensembles to load
        ensemle_set_name: str = name of enesemble-set
        time_index: str = timeseries steps
        column_keys: tuple = pre filtered vectors
        iorens: str =
        refens: str = reference ensemble
    Retuns:
        delta-vals-dataframe
    """

    column_keys = list(column_keys) if isinstance(
        column_keys, (list, tuple)) else None

    ensset = load_ensemble_set(
        ensemble_paths=ensemble_paths,
        ensemble_set_name=ensemble_set_name
    )

    return (ensset[iorens] - ensset[refens]).get_smry(
        column_keys=column_keys,
        time_index=time_index,
    )
