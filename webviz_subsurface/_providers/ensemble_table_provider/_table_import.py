import glob
import logging
import os
import re
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

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

        real = get_realization_number_from_path(path)

        if real is None:
            raise ValueError(f"Unable to determine realization number for file: {path}")

        if validated_reals is not None and real not in validated_reals:
            LOGGER.warning(f"Skipping realization {real} no OK file found")
            continue

        file_list.append(FileEntry(real=real, filename=path))

    # Sort the file entries on realization number
    file_list = sorted(file_list, key=lambda e: e.real)
    return file_list


def get_realization_number_from_path(path: str) -> int:
    realidxregexp = re.compile(r"realization-(\d+)")

    for path_comp in reversed(path.split(os.path.sep)):
        realmatch = re.match(realidxregexp, path_comp)
        if realmatch:
            return int(realmatch.group(1))

    raise ValueError(f"Unable to determine realization number for path: {path}")


def validate_ralizations(ens_path: str, filterfile: str) -> List[int]:
    if filterfile is not None:
        ensemble_paths = glob.glob(os.path.join(ens_path, filterfile))
    else:
        ensemble_paths = glob.glob(ens_path)
    return [get_realization_number_from_path(path) for path in ensemble_paths]


def _load_table_from_csv_file(entry: FileEntry) -> pd.DataFrame:
    LOGGER.debug(f"loading table real={entry.real}: {entry.filename}")
    df = pd.read_csv(entry.filename)
    df["REAL"] = int(entry.real)
    return df


def load_per_real_csv_file(
    ens_path: str, csv_file_rel_path: str, filterfile: str = "OK"
) -> pd.DataFrame:
    LOGGER.debug(f"load_per_realization_arrow_unsmry_files() starting - {ens_path}")
    LOGGER.debug(
        f"looking for .arrow files using relative pattern: {csv_file_rel_path}"
    )
    timer = PerfTimer()

    validated_reals = validate_ralizations(ens_path, filterfile)

    globpattern = os.path.join(ens_path, csv_file_rel_path)
    files_to_process = _discover_files(globpattern, validated_reals)
    if len(files_to_process) == 0:
        LOGGER.warning(f"No csv files were discovered in: {ens_path}")
        LOGGER.warning(f"Glob pattern used: {globpattern}")
        return pd.DataFrame()

    with ProcessPoolExecutor() as executor:
        tables = executor.map(_load_table_from_csv_file, files_to_process)

    LOGGER.debug(f"load_per_real_csv_file() " f"finished in: {timer.elapsed_s():.2f}s")
    return pd.concat(tables)


def _load_table_from_parameters_file(entry: FileEntry) -> dict:
    LOGGER.debug(f"loading table real={entry.real}: {entry.filename}")
    data: Dict[str, Any] = {"REAL": int(entry.real)}
    with open(entry.filename, "r") as f:
        for line in f:
            param, value = line.split()
            data[param] = parse_number_from_string(value)
    return data


def load_per_real_parameters_file(
    ens_path: str, filterfile: str = "OK"
) -> pd.DataFrame:
    parameter_file = "parameters.txt"
    LOGGER.debug(f"load_per_real_parameters_file() starting - {ens_path}")
    LOGGER.debug(f"looking for files using relative pattern: {parameter_file}")
    timer = PerfTimer()

    validated_reals = validate_ralizations(ens_path, filterfile)

    globpattern = os.path.join(ens_path, parameter_file)
    files_to_process = _discover_files(globpattern, validated_reals)
    if len(files_to_process) == 0:
        LOGGER.warning(f"No csv files were discovered in: {ens_path}")
        LOGGER.warning(f"Glob pattern used: {globpattern}")
        return pd.DataFrame()

    with ProcessPoolExecutor() as executor:
        tables = executor.map(_load_table_from_parameters_file, files_to_process)

    LOGGER.debug(
        f"load_per_real_parameters_file() " f"finished in: {timer.elapsed_s():.2f}s"
    )
    return pd.DataFrame(tables)
