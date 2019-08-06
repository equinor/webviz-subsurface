import os
try:
    import fmu.ensemble
except ImportError:  # fmu.ensemble is an optional dependency, e.g.
    pass             # for a portable webviz instance, it is never used.

import pandas as pd
from webviz_config.common_cache import cache
from webviz_config.webviz_store import webvizstore


@cache.memoize(timeout=cache.TIMEOUT)
def scratch_ensemble(ensemble_name, ensemble_path):
    return fmu.ensemble.ScratchEnsemble(ensemble_name, ensemble_path)


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def extract_volumes(ensemble_paths, volfolder, volfiles) -> pd.DataFrame:
    dfs = []
    for ens_name, ens_path in list(ensemble_paths):
        ens_dfs = []
        ens = scratch_ensemble(ens_name, ens_path)
        for volname, volfile in volfiles:
            path = os.path.join(volfolder, volfile)
            df = ens.load_csv(path)
            df['SOURCE'] = volname
            df['ENSEMBLE'] = ens_name
            ens_dfs.append(df)
        dfs.append(pd.concat(ens_dfs))
    return pd.concat(dfs)
