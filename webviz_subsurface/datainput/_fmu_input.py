import os
from pathlib import Path
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
        # Extracts realization runpath from the EnsembleSet.ScratchEnsemble.Realization object
        lambda x: ens_set[x["ENSEMBLE"]][x["REAL"]].runpath(),
        axis=1,
    )
    return df.sort_values(by=["ENSEMBLE", "REAL"])


@cache.memoize(timeout=cache.TIMEOUT)
def find_surfaces(ensemble_paths: tuple, suffix="*.gri", delimiter="--"):
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
    # Create list of all files in all realizations in all ensembles
    files = []
    for _, path in ensemble_paths:
        path = Path(path)
        files += glob.glob(str(path / "share" / "results" / "maps" / suffix))

    # Store surface name, attribute and date as Pandas dataframe
    df = pd.DataFrame(
        [Path(f).stem.split(delimiter) for f in files],
        columns=["name", "attribute", "date"],
    )

    # Group dataframe by surface attribute and return unique names and dates
    return {
        attr: {
            "names": list(dframe["name"].unique()),
            "dates": list(dframe["date"].unique()),
        }
        for attr, dframe in df.groupby("attribute")
    }
