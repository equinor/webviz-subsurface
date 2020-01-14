import os

import pandas as pd
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

try:
    import fmu.ensemble
except ImportError:  # fmu.ensemble is an optional dependency, e.g.
    pass  # for a portable webviz instance, it is never used.


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def scratch_ensemble(ensemble_name, ensemble_path):
    return fmu.ensemble.ScratchEnsemble(ensemble_name, ensemble_path)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def extract_volumes(ensemble_paths, volfolder, volfiles) -> pd.DataFrame:
    """Aggregates volumetric files from an FMU ensemble.
    Files must be stored on standardized csv format.
    """
    dfs = []
    for ens_name, ens_path in ensemble_paths.items():
        ens_dfs = []
        ens = scratch_ensemble(ens_name, ens_path)
        for volname, volfile in volfiles.items():
            try:
                path = os.path.join(volfolder, volfile)
                df = ens.load_csv(path)
                df["SOURCE"] = volname
                df["ENSEMBLE"] = ens_name
                ens_dfs.append(df)
            except ValueError:
                pass
        try:
            dfs.append(pd.concat(ens_dfs))
        except ValueError:
            pass
    if not dfs:
        raise ValueError(
            f"Error when aggregating inplace volumetric files: {list(volfiles)}. "
            f"Ensure that the files are present in relative folder {volfolder}"
        )
    return pd.concat(dfs)
