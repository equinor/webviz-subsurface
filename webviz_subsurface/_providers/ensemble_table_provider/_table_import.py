import glob
import logging
import os
import re
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from typing import Any, Dict, List

import pandas as pd

from webviz_subsurface._utils.formatting import parse_number_from_string
from webviz_subsurface._utils.perf_timer import PerfTimer

LOGGER = logging.getLogger(__name__)


@dataclass
class FileEntry:
    real: int
    filename: str


def _discover_files(
    globpattern: str, validated_reals: List[int] = None
) -> List[FileEntry]:
    globbedpaths = glob.glob(globpattern)

    visited_folders = set()

    file_list: list = []
    for path in globbedpaths:
        this_folder = os.path.dirname(path)
        if this_folder in visited_folders:
            raise ValueError(f"Multiple matches found in folder: {this_folder}")
        visited_folders.add(this_folder)

        real = _get_realization_number_from_path(path)

        if real is None:
            raise ValueError(f"Unable to determine realization number for file: {path}")

        if validated_reals is not None and real not in validated_reals:
            continue

        file_list.append(FileEntry(real=real, filename=path))

    # Sort the file entries on realization number
    file_list = sorted(file_list, key=lambda e: e.real)
    return file_list


def _get_realization_number_from_path(path: str) -> int:
    realidxregexp = re.compile(r"realization-(\d+)")

    for path_comp in reversed(path.split(os.path.sep)):
        realmatch = re.match(realidxregexp, path_comp)
        if realmatch:
            return int(realmatch.group(1))

    raise ValueError(f"Unable to determine realization number for path: {path}")


def _validate_fmu_realizations(
    ens_path: str, drop_failed_realizations: bool = True
) -> List[int]:
    success_file = "OK"
    all_ensemble_paths = glob.glob(ens_path)
    realizations = [
        _get_realization_number_from_path(path) for path in all_ensemble_paths
    ]
    if drop_failed_realizations:
        LOGGER.info(f"Filtering realizations on {success_file} file")
        ensemble_paths = glob.glob(os.path.join(ens_path, success_file))
        validated_realizations = list(
            map(_get_realization_number_from_path, ensemble_paths)
        )
        filtered_realizations = [
            x for x in realizations if x not in validated_realizations
        ]
        LOGGER.info(
            f"Dropped failed realizations from ensemble {ens_path}: {sorted(filtered_realizations)}"
        )

        if not validated_realizations:
            raise ValueError(
                f"All realizations have failed in ensemble {ens_path}. (i.e. 'OK' file missing)"
            )
        return validated_realizations

    return realizations


def _load_table_from_csv_file(entry: FileEntry) -> pd.DataFrame:
    LOGGER.debug(f"loading table real={entry.real}: {entry.filename}")
    df = pd.read_csv(entry.filename)
    df["REAL"] = int(entry.real)
    return df


def load_per_real_csv_file(
    ens_path: str, csv_file_rel_path: str, drop_failed_realizations: bool = True
) -> pd.DataFrame:
    LOGGER.debug(f"load_per_real_csv_file() starting - {ens_path}")
    LOGGER.debug(f"looking for .csv files using relative pattern: {csv_file_rel_path}")
    timer = PerfTimer()

    validated_reals = _validate_fmu_realizations(ens_path, drop_failed_realizations)

    globpattern = os.path.join(ens_path, csv_file_rel_path)
    files_to_process = _discover_files(globpattern, validated_reals)
    if len(files_to_process) == 0:
        LOGGER.debug(f"No csv files were discovered in: {ens_path}")
        LOGGER.debug(f"Glob pattern used: {globpattern}")
        return pd.DataFrame()

    with ProcessPoolExecutor() as executor:
        tables = executor.map(_load_table_from_csv_file, files_to_process)

    LOGGER.debug(f"load_per_real_csv_file() " f"finished in: {timer.elapsed_s():.2f}s")
    return pd.concat(tables)


def _load_table_from_parameters_file(entry: FileEntry) -> dict:
    LOGGER.debug(f"loading table real={entry.real}: {entry.filename}")
    data: Dict[str, Any] = {"REAL": int(entry.real)}
    with open(entry.filename, "r") as paramfile:
        for line in paramfile:
            param, *valuelist = line.split()
            # Remove leading and trailing qoutation marks.
            # This can happen if a parameter value includes a space
            if len(valuelist) > 1:
                valuelist = [val.strip('"') for val in valuelist]
            value = " ".join(valuelist)
            data[param] = parse_number_from_string(value)
    return data


def load_per_real_parameters_file(
    ens_path: str, drop_failed_realizations: bool = True
) -> pd.DataFrame:
    parameter_file = "parameters.txt"
    LOGGER.debug(f"load_per_real_parameters_file() starting - {ens_path}")
    LOGGER.debug(f"looking for files using relative pattern: {parameter_file}")
    timer = PerfTimer()

    validated_reals = _validate_fmu_realizations(ens_path, drop_failed_realizations)

    globpattern = os.path.join(ens_path, parameter_file)
    files_to_process = _discover_files(globpattern, validated_reals)
    if len(files_to_process) == 0:
        LOGGER.warning(f"No 'parameter.txt' files were discovered in: {ens_path}")
        LOGGER.warning(f"Glob pattern used: {globpattern}")
        return pd.DataFrame()

    with ProcessPoolExecutor() as executor:
        tables = executor.map(_load_table_from_parameters_file, files_to_process)

    LOGGER.debug(
        f"load_per_real_parameters_file() " f"finished in: {timer.elapsed_s():.2f}s"
    )
    return pd.DataFrame(tables)
