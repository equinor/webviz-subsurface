from typing import List, Dict
import os
import logging
import re
import glob
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor

# from fmu.ensemble import ScratchEnsemble

import pyarrow as pa

from webviz_subsurface.ert_jobs.smry2arrow import _load_smry_into_table

from .ensemble_summary_provider_resampling import (
    Frequency,
    resample_single_real_table,
)

from .._utils.perf_timer import PerfTimer


LOGGER = logging.getLogger(__name__)


@dataclass
class FileEntry:
    real: int
    filename: str


# -------------------------------------------------------------------------
def _read_and_build_table_for_one_real(entry: FileEntry) -> pa.Table:
    LOGGER.debug(f"real={entry.real}: {entry.filename}")
    return _load_smry_into_table(entry.filename)


# -------------------------------------------------------------------------
def load_per_realization_smry_tables_using_smry2arrow(
    ens_path: str,
) -> Dict[int, pa.Table]:

    LOGGER.debug(
        f"load_per_realization_smry_tables_using_smry2arrow() starting - {ens_path}"
    )
    timer = PerfTimer()

    realidxregexp = re.compile(r"realization-(\d+)")
    globbedpaths = sorted(glob.glob(ens_path + "/eclipse/model/*.UNSMRY"))

    files_to_process: List[FileEntry] = []

    for path in globbedpaths:
        real = None
        for path_comp in reversed(path.split(os.path.sep)):
            realmatch = re.match(realidxregexp, path_comp)
            if realmatch:
                real = int(realmatch.group(1))
                files_to_process.append(FileEntry(real=real, filename=path))
                break

    files_to_process = sorted(files_to_process, key=lambda e: e.real)

    # !!!!!!!
    # !!!!!!!
    # Test accessing via FMU Ensamble package
    # scratch_ensemble = ScratchEnsemble(
    #     "tempEnsName", paths=ens_path, autodiscovery=True
    # )
    # for realidx, real in scratch_ensemble.realizations.items():
    #     files_df = real.files
    #     print(files_df.head(50))

    # LOGGER.debug(f"file discovery took: {timer.elapsed_s():.2f}s")

    # !!!!!!!!!!!!!!!!!!!!!!
    # files_to_process = files_to_process[0:10]

    per_real_tables: Dict[int, pa.Table] = {}

    with ProcessPoolExecutor() as executor:
        futures = executor.map(_read_and_build_table_for_one_real, files_to_process)
    for i, table in enumerate(futures):
        real = files_to_process[i].real
        per_real_tables[real] = table

    # for entry in files_to_process:
    #     table = _read_and_build_table_for_one_real(entry)
    #     per_real_tables[entry.real] = table

    LOGGER.debug(
        f"load_per_realization_smry_tables_using_smry2arrow() "
        f"finished in: {timer.elapsed_s():.2f}s"
    )

    return per_real_tables


# -------------------------------------------------------------------------
def resample_per_real_tables(
    per_real_tables: Dict[int, pa.Table], freq: Frequency
) -> Dict[int, pa.Table]:
    resampled_tables: Dict[int, pa.Table] = {}
    for real_num, table in per_real_tables.items():
        resampled_tables[real_num] = resample_single_real_table(table, freq)

    return resampled_tables
