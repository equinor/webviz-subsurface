import glob
import warnings
from pathlib import Path
from typing import List, Optional, Union

import pandas as pd
from fmu.ensemble import EnsembleSet, ScratchEnsemble
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def scratch_ensemble(
    ensemble_name: str, ensemble_path: Path, filter_file: Union[str, None] = "OK"
) -> ScratchEnsemble:
    return (
        ScratchEnsemble(ensemble_name, ensemble_path)
        if filter_file is None
        else ScratchEnsemble(ensemble_name, ensemble_path).filter(filter_file)
    )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def load_ensemble_set(
    ensemble_paths: dict,
    ensemble_set_name: str = "EnsembleSet",
    filter_file: Union[str, None] = "OK",
) -> EnsembleSet:
    return EnsembleSet(
        ensemble_set_name,
        [
            scratch_ensemble(ens_name, ens_path, filter_file)
            for ens_name, ens_path in ensemble_paths.items()
        ],
    )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def load_parameters(
    ensemble_paths: dict,
    ensemble_set_name: str = "EnsembleSet",
    filter_file: Union[str, None] = "OK",
) -> pd.DataFrame:
    return load_ensemble_set(ensemble_paths, ensemble_set_name, filter_file).parameters


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
    time_index: Optional[Union[list, str]] = None,
    column_keys: Optional[list] = None,
) -> pd.DataFrame:

    return load_ensemble_set(ensemble_paths, ensemble_set_name).get_smry(
        time_index=time_index, column_keys=column_keys
    )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def load_smry_meta(
    ensemble_paths: dict,
    ensemble_set_name: str = "EnsembleSet",
    column_keys: Optional[list] = None,
) -> pd.DataFrame:
    """Finds metadata for the summary vectors in the ensemble set.
    Note that we assume the same units for all ensembles.
    (meaning that we update/overwrite when checking the next ensemble)
    """
    ensemble_set = load_ensemble_set(ensemble_paths, ensemble_set_name)
    smry_meta = {}
    for ensname in ensemble_set.ensemblenames:
        smry_meta.update(ensemble_set[ensname].get_smry_meta(column_keys=column_keys))
    return pd.DataFrame(smry_meta).transpose()


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


def find_sens_type(senscase: str) -> Optional[str]:
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
def find_surfaces(
    ensemble_paths: dict,
    surface_folder: str = "share/results/maps",
    surface_files: Optional[List] = None,
    suffix: str = "*.gri",
    delimiter: str = "--",
) -> pd.DataFrame:
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
    for _, ensdf in get_realizations(ensemble_paths=ensemble_paths).groupby("ENSEMBLE"):
        ens_files = []
        for _real_no, realdf in ensdf.groupby("REAL"):
            runpath = realdf.iloc[0]["RUNPATH"]
            for realpath in glob.glob(str(Path(runpath) / surface_folder / suffix)):
                filename = Path(realpath)
                if surface_files and filename.name not in surface_files:
                    continue
                stem = filename.stem.split(delimiter)
                if len(stem) >= 2:
                    ens_files.append(
                        {
                            "path": realpath,
                            "name": stem[0],
                            "attribute": stem[1],
                            "date": stem[2] if len(stem) >= 3 else None,
                            **realdf.iloc[0],
                        }
                    )
        if not ens_files:
            warnings.warn(f"No surfaces found for ensemble located at {runpath}.")
        else:
            files.extend(ens_files)

    # Store surface name, attribute and date as Pandas dataframe
    if not files:
        raise ValueError(
            "No surfaces found! Ensure that surfaces file are stored "
            "at share/results/maps in each ensemble and is following "
            "the FMU naming standard (name--attribute[--date].gri)"
        )
    return pd.DataFrame(files)
