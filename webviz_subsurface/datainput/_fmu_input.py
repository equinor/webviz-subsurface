import pandas as pd

try:
    from fmu.ensemble import ScratchEnsemble, EnsembleSet
except ImportError:
    pass
from webviz_config.common_cache import cache
from webviz_config.webviz_store import webvizstore


@cache.memoize(timeout=cache.TIMEOUT)
def load_ensemble_set(ensemble_paths: tuple, ensemble_set_name: str = "EnsembleSet"):
    return EnsembleSet(
        ensemble_set_name,
        [ScratchEnsemble(ens_name, ens_path) for ens_name, ens_path in ensemble_paths],
    )


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def load_parameters(
    ensemble_paths: tuple, ensemble_set_name: str = "EnsembleSet"
) -> pd.DataFrame:

    return load_ensemble_set(ensemble_paths, ensemble_set_name).parameters


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def get_realizations(
    ensemble_paths: tuple, ensemble_set_name: str = "EnsembleSet"
) -> pd.DataFrame:
    ens_set = load_ensemble_set(ensemble_paths, ensemble_set_name)
    df = ens_set.parameters.get(["ENSEMBLE", "REAL"])
    df["SENSCASE"] = ens_set.parameters.get("SENSCASE")
    df["SENSNAME"] = ens_set.parameters.get("SENSNAME")
    df["RUNPATH"] = df.apply(
        lambda x: ens_set[x["ENSEMBLE"]][x["REAL"]].runpath(), axis=1
    )
    return df.sort_values(by=["ENSEMBLE", "REAL"])
