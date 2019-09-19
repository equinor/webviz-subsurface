import pandas as pd
from fmu.ensemble import ScratchEnsemble, EnsembleSet
from webviz_config.common_cache import cache
from webviz_config.webviz_store import webvizstore

@cache.memoize(timeout=cache.TIMEOUT)
def load_ensemble_set(
    ensemble_paths: tuple,
    ensemble_set_name: str = 'EnsembleSet'):
	return EnsembleSet(
        ensemble_set_name,
        [ScratchEnsemble(ens_name, ens_path)
         for ens_name, ens_path in ensemble_paths]
    )

@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def load_parameters(
        ensemble_paths: tuple,
        ensemble_set_name: str = 'EnsembleSet') -> pd.DataFrame:

    return load_ensemble_set(ensemble_paths, ensemble_set_name).parameters
