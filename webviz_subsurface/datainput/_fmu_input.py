import os
import glob
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
    """Extracts realization info from parameters.txt.
    The information extracted is the ensemble name, realization number,
    realization local runpath, sensitivity name and sensitivity case.
    The sensitivty name and case is only relevant if a design matrix is used. If the ensemble
    is a monte carlo / history matching run this information will be undefined.
    
    Returns a pandas dataframe with columns: ENSEMBLE, REAL, RUNPATH, SENSNAME, SENSCASE
    """
    ens_set = load_ensemble_set(ensemble_paths, ensemble_set_name)
    df = ens_set.parameters.get(["ENSEMBLE", "REAL"])
    df["SENSCASE"] = ens_set.parameters.get("SENSCASE")
    df["SENSNAME"] = ens_set.parameters.get("SENSNAME")
    df["RUNPATH"] = df.apply(
        #Extracts realization runpath from the EnsembleSet.ScratchEnsemble.Realization object
        lambda x: ens_set[x["ENSEMBLE"]][x["REAL"]].runpath(), axis=1
    )
    return df.sort_values(by=["ENSEMBLE", "REAL"])


@cache.memoize(timeout=cache.TIMEOUT)
def find_surfaces(ensemble_paths: tuple, suffix="*.gri"):
    """Reads surface file names stored in standard FMU format, and returns a dictionary
    on the following format:
    surface_property:
        names:
            - some_surface_name
            - another_surface_name
        dates:
            - some_date
            - another_date
    """

    files = []
    for _, path in ensemble_paths:
        files.extend(glob.glob(os.path.join(path, "share", "results", "maps", suffix)))

    files = [os.path.basename(f.split(".gri")[0]) for f in files]
    files = [f.split("--") for f in files]
    arr = []
    for f in files:
        data = {}
        try:
            data["attribute"] = f[1]
        except IndexError:
            continue
        try:
            data["name"] = f[0]
        except IndexError:
            data["name"] = None
        try:
            data["date"] = f[2]
        except IndexError:
            data["date"] = None
        arr.append(data)

    df = pd.DataFrame(arr)

    context = {}
    for attr, dframe in df.groupby("attribute"):
        context[attr] = {
            "names": list(dframe["name"].unique()),
            "dates": list(dframe["date"].unique()),
        }

    return context
