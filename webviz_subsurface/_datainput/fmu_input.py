from pathlib import Path
import glob
from typing import Union

import pandas as pd
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

try:
    from fmu.ensemble import ScratchEnsemble, EnsembleSet
except ImportError:
    pass


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def scratch_ensemble(ensemble_name, ensemble_path):
    return ScratchEnsemble(ensemble_name, ensemble_path)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def load_ensemble_set(
    ensemble_paths: dict,
    ensemble_set_name: str = "EnsembleSet",
    filter_file: Union[str, None] = "OK",
):
    return EnsembleSet(
        ensemble_set_name,
        [
            ScratchEnsemble(ens_name, ens_path)
            if filter_file is None
            else ScratchEnsemble(ens_name, ens_path).filter(filter_file)
            for ens_name, ens_path in ensemble_paths.items()
        ],
    )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def load_parameters(
    ensemble_paths: dict, ensemble_set_name: str = "EnsembleSet"
) -> pd.DataFrame:

    return load_ensemble_set(ensemble_paths, ensemble_set_name).parameters


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def load_csv(
    ensemble_paths: dict, csv_file: str, ensemble_set_name: str = "EnsembleSet"
) -> pd.DataFrame:

    return load_ensemble_set(ensemble_paths, ensemble_set_name).load_csv(csv_file)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def load_smry(
    ensemble_paths: dict,
    ensemble_set_name: str = "EnsembleSet",
    time_index=str,
    column_keys=list,
) -> pd.DataFrame:

    return load_ensemble_set(ensemble_paths, ensemble_set_name).get_smry(
        time_index=time_index, column_keys=column_keys
    )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def get_realizations(
    ensemble_paths: dict, ensemble_set_name: str = "EnsembleSet"
) -> pd.DataFrame:
    """Extracts realization info from a fmu.ensemble.EnsembleSet
    The information extracted is the ensemble name, realization number,
    realization local runpath, sensitivity name, sensitivity case and sensitivity type.
    The sensitivtiy information is only relevant if a design matrix is used. If the ensemble
    is a full monte carlo / history matching run this information will be undefined.

    Returns a pandas dataframe with columns: ENSEMBLE, REAL, RUNPATH, SENSNAME, SENSCASE, SENSTYPE
    """
    ens_set = load_ensemble_set(ensemble_paths, ensemble_set_name)
    df = ens_set.parameters.get(["ENSEMBLE", "REAL"])
    df["SENSCASE"] = ens_set.parameters.get("SENSCASE")
    df["SENSNAME"] = ens_set.parameters.get("SENSNAME")
    df["SENSTYPE"] = df.apply(lambda row: find_sens_type(row.SENSCASE), axis=1)
    df["RUNPATH"] = df.apply(
        # Extracts realization runpath from the EnsembleSet.ScratchEnsemble.Realization object
        lambda x: ens_set[x["ENSEMBLE"]][x["REAL"]].runpath(),
        axis=1,
    )
    return df.sort_values(by=["ENSEMBLE", "REAL"])


def find_sens_type(senscase):
    """Finds sensitivity type from sensitivty case.
    If sensitivity case is 'p10_p90', sensitivity type is montecarlo,
    else sensitivity type is set to 'scalar'.
    """
    if not senscase:
        return None

    if senscase == "p10_p90":
        return "mc"

    return "scalar"


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def find_surfaces(ensemble_paths: dict, suffix="*.gri", delimiter="--") -> pd.DataFrame:
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
    for path in ensemble_paths.values():
        path = Path(path)
        for realpath in glob.glob(str(path / "share" / "results" / "maps" / suffix)):
            stem = Path(realpath).stem.split(delimiter)
            if len(stem) >= 2:
                files.append(
                    {
                        "path": realpath,
                        "name": stem[0],
                        "attribute": stem[1],
                        "date": stem[2] if len(stem) >= 3 else None,
                    }
                )

    # Store surface name, attribute and date as Pandas dataframe
    return pd.DataFrame(files)
