
try:
    import fmu.ensemble
except ImportError:  # fmu.ensemble is an optional dependency, e.g.
    pass             # for a portable webviz instance, it is never used.

import pandas as pd
from pathlib import Path
from webviz_config.common_cache import cache
from webviz_config.webviz_store import webvizstore


@cache.memoize(timeout=cache.TIMEOUT)
def scratch_ensemble(ensemble_name, ensemble_path):
    return fmu.ensemble.ScratchEnsemble(ensemble_name, ensemble_path)

@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def extract_volumes(ensemble_path, ensemble_name) -> pd.DataFrame:
    volfile='share/results/volumes/volumes.csv'
    dfs = []
    ens = scratch_ensemble(ensemble_name, ensemble_path)
    df = ens.load_csv(volfile)
    df['ENSEMBLE'] = ens._name
    return df
    # dfs.append(df)
    # return pd.concat(dfs)