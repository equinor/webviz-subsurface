import glob
import logging
import os
import re
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from typing import Dict, List, Set

import pyarrow as pa

from webviz_subsurface._utils.perf_timer import PerfTimer

LOGGER = logging.getLogger(__name__)


@dataclass
class FileEntry:
    real: int
    filename: str


def _discover_arrow_unsmry_files(globpattern: str) -> List[FileEntry]:

    realidxregexp = re.compile(r"realization-(\d+)")

    globbedpaths = glob.glob(globpattern)

    visited_folders: Set[str] = set()

    file_list: List[FileEntry] = []
    for path in globbedpaths:
        this_folder = os.path.dirname(path)
        if this_folder in visited_folders:
            raise ValueError(f"Multiple matches found in folder: {this_folder}")
        visited_folders.add(this_folder)

        real = None
        for path_comp in reversed(path.split(os.path.sep)):
            realmatch = re.match(realidxregexp, path_comp)
            if realmatch:
                real = int(realmatch.group(1))
                break

        if real is None:
            raise ValueError(f"Unable to determine realization number for file: {path}")

        file_list.append(FileEntry(real=real, filename=path))

    # Sort the file entries on realization number
    file_list = sorted(file_list, key=lambda e: e.real)
    return file_list


def _load_table_from_arrow_file(entry: FileEntry) -> pa.Table:
    LOGGER.debug(f"loading table real={entry.real}: {entry.filename}")
    source = pa.memory_map(entry.filename, "r")
    reader = pa.ipc.RecordBatchFileReader(source)
    return reader.read_all()


def load_per_realization_arrow_unsmry_files(
    ens_path: str, rel_file_pattern: str
) -> Dict[int, pa.Table]:
    """Load summary data stored in per-realization arrow files.
    Returns dictionary containing a PyArrow table for each realization, indexed by
    realization number.

    `rel_file_pattern` denotes a file pattern relative to the realization's runpath,
    typical value is: "share/results/unsmry/*.arrow"
    """

    LOGGER.debug(f"load_per_realization_arrow_unsmry_files() starting - {ens_path}")
    LOGGER.debug(f"looking for .arrow files using relative pattern: {rel_file_pattern}")
    timer = PerfTimer()

    per_real_tables: Dict[int, pa.Table] = {}
    globpattern = os.path.join(ens_path, rel_file_pattern)
    files_to_process = _discover_arrow_unsmry_files(globpattern)
    if len(files_to_process) == 0:
        LOGGER.warning(f"No arrow files were discovered in: {ens_path}")
        LOGGER.warning(f"Glob pattern used: {globpattern}")
        return per_real_tables

    with ProcessPoolExecutor() as executor:
        futures = executor.map(_load_table_from_arrow_file, files_to_process)
    for i, table in enumerate(futures):
        real = files_to_process[i].real
        per_real_tables[real] = table

    # for entry in files_to_process:
    #     table = _load_table_from_arrow_file(entry)
    #     per_real_tables[entry.real] = table

    LOGGER.debug(
        f"load_per_realization_arrow_unsmry_files() "
        f"finished in: {timer.elapsed_s():.2f}s"
    )

    return per_real_tables
