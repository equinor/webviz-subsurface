#!/usr/bin/env python
"""Convert UNSMRY file to Apache Arrow IPC file format (also known as Feather V2)
"""

import argparse
import json
import logging
import re
import time
from pathlib import Path
from typing import Dict, Iterable, List

import pyarrow as pa
from ecl.summary import EclSum, EclSumKeyWordVector
from pyarrow import feather

logger = logging.getLogger(__name__)


DESCRIPTION: str = """
Convert UNSMRY file to Apache Arrow IPC file format (also known as Feather V2)
"""
CATEGORY: str = "utility.eclipse"
EXAMPLES: str = """
Convert and output summary data in SOME.UNSMRY file to an Arrow IPC file named unsmry.arrow
this in the ert workflow:

    FORWARD_MODEL SMRY2ARROW(<INPUT>=eclipse/model/SOME.UNSMRY)

"""


def _get_parser() -> argparse.ArgumentParser:
    """Setup parser for command line options"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=DESCRIPTION,
    )
    parser.add_argument(
        "eclbase",
        type=Path,
        help="Eclipse base name",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file",
        default=Path() / "share" / "results" / "tables" / "unsmry.arrow",
    )
    return parser


# This logic is copied from well_connection_status.py.
# Should be refactored so that the two modules share a common implementation.
def _is_cpi_column(column_name: str) -> bool:
    return bool(re.match("^CPI:[A-Z0-9_-]{1,8}:[0-9]+,[0-9]+,[0-9]+$", column_name))


def _create_smry_meta_dict(
    eclsum: EclSum, column_names: Iterable[str]
) -> Dict[str, dict]:
    """Builds dictionary containing metadata for all the specified summary columns"""
    smry_meta = {}

    for col_name in column_names:
        col_meta = {}
        col_meta["unit"] = eclsum.unit(col_name)
        col_meta["is_total"] = eclsum.is_total(col_name)
        col_meta["is_rate"] = eclsum.is_rate(col_name)
        col_meta["is_historical"] = eclsum.smspec_node(col_name).is_historical()
        col_meta["keyword"] = eclsum.smspec_node(col_name).keyword
        col_meta["wgname"] = eclsum.smspec_node(col_name).wgname

        num = eclsum.smspec_node(col_name).get_num()
        if num is not None:
            col_meta["get_num"] = num

        smry_meta[col_name] = col_meta

    return smry_meta


def _load_smry_into_table(smry_filename: str) -> pa.Table:
    """
    Reads data from SMRY file into PyArrow Table.
    DATE column is stored as an Arrow timetamp with ms resolution, timestamp[ms]
    All numeric columns will be stored as 32 bit float
    Summary meta data will be attached per field/column of the table's schema under the
    'smry_meta' key
    """

    eclsum = EclSum(smry_filename, include_restart=False, lazy_load=False)

    # For now, we go via a set to prune out duplicate entries being returned by EclSumKeyWordVector,
    # see: https://github.com/equinor/ecl/issues/816#issuecomment-865881283
    column_names: List[str] = list(set(EclSumKeyWordVector(eclsum, add_keywords=True)))

    # Exclude CPI columns from export
    org_col_count = len(column_names)
    column_names = [colname for colname in column_names if not _is_cpi_column(colname)]
    if len(column_names) != org_col_count:
        logger.info(
            f"Excluding {org_col_count - len(column_names)} CPI columns from export"
        )

    # Fetch the dates as a numpy array with ms resolution
    np_dates_ms = eclsum.numpy_dates

    smry_meta_dict = _create_smry_meta_dict(eclsum, column_names)

    # Datatypes to use for DATE column and all the numeric columns
    dt_timestamp_ms = pa.timestamp("ms")
    dt_float32 = pa.float32()

    # Build schema for the table
    field_list: List[pa.Field] = []
    field_list.append(pa.field("DATE", dt_timestamp_ms))
    for colname in column_names:
        field_metadata = {b"smry_meta": json.dumps(smry_meta_dict[colname])}
        field_list.append(pa.field(colname, dt_float32, metadata=field_metadata))

    schema = pa.schema(field_list)

    # Now extract all the summary vectors one by one
    # We do this through EclSum.numpy_vector() instead of EclSum.pandas_frame() since
    # the latter throws an exception if the SMRY data has timestamps beyond 2262,
    # see: https://github.com/equinor/ecl/issues/802
    column_arrays = [np_dates_ms]

    for colname in column_names:
        colvector = eclsum.numpy_vector(colname)
        column_arrays.append(colvector)

    table = pa.table(column_arrays, schema=schema)

    return table


def smry2arrow(smry_filename: Path, arrow_filename: Path) -> None:
    start_s = time.perf_counter()

    logger.debug(f"Reading SMRY data from: {smry_filename}")
    table: pa.Table = _load_smry_into_table(str(smry_filename))
    read_s = time.perf_counter() - start_s

    # Writing here is done through the feather import, but could also be done using
    # pa.RecordBatchFileWriter.write_table() with a few pa.ipc.IpcWriteOptions().
    # It is convenient to use feather since it has ready configured defaults and the
    # actual file format is the same (https://arrow.apache.org/docs/python/feather.html)
    logger.debug(f"Writing {table.shape} arrow file to: {arrow_filename}")
    feather.write_feather(table, dest=arrow_filename)

    logger.debug(
        f"Conversion took: {(time.perf_counter() - start_s):.2f}s (read={read_s:.2f}s)"
    )


def main() -> None:
    """Entry point from command line"""
    parser = _get_parser()
    args = parser.parse_args()

    # Create the output folder if it doesn't exist
    args.output.parent.mkdir(parents=True, exist_ok=True)

    smry2arrow(args.eclbase.with_suffix(".UNSMRY"), args.output)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()
