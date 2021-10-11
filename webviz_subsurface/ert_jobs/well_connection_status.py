#!/usr/bin/env python
"""Exctracts connection status history for each compdat connection that
is included in the summary data on the form CPI:WELL,I,J,K. One line is
added to the export every time a connection changes status. It is OPEN when
CPI>0 and SHUT when CPI=0. The earliest date for any connection will be OPEN,
i.e a cell can not be SHUT before it has been OPEN. This means that any cells
that are always SHUT will be excluded.

The output data set is very sparse compared to the CPI summary data.
"""
import argparse
import re
from pathlib import Path
from typing import Any, List, Set, Tuple

import numpy as np
import pandas as pd
from ecl.summary import EclSum, EclSumKeyWordVector

from webviz_subsurface.plugins._well_completions import WELL_CONNECTION_STATUS_FILE

DESCRIPTION: str = """
Export connection status data on sparse form from CPI summary data.
"""
CATEGORY: str = "utility.eclipse"
EXAMPLES: str = """
Extracts well connection status history from the .UNSMRY file by running
this in the ert workflow:

    FORWARD_MODEL WELL_CONNECTION_STATUS(<ECLBASE>=eclipse/model/SOME)

The default output file is share/results/tables/well_connection_status.parquet
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
        default=WELL_CONNECTION_STATUS_FILE,
    )
    return parser


def _get_status_changes(
    dates: np.ndarray, conn_values: np.ndarray
) -> List[Tuple[Any, str]]:
    """Extracts the status history of a single connection as a list of tuples
    on the form (date, status)
    """
    status_changes = []
    prev_value = 0
    for date, value in zip(dates, conn_values):
        if value > 0 and prev_value == 0:
            status_changes.append((date, "OPEN"))
        elif prev_value > 0 and value == 0:
            status_changes.append((date, "SHUT"))
        prev_value = value
    return status_changes


def _extract_well_connection_status(filename: Path) -> pd.DataFrame:
    # pylint: disable=too-many-locals
    """Exctracts well connection status history for each compdat connection that
    is included in the summary data on the form CPI:WELL,I,J,K.

    From the CPI time series it is possible to extract the status of the connection
    because it is 0 when the connection is SHUT and >0 when the connection is open.

    The output from this function is one row for every time a connection changes
    status. The earliest date for any connection will be OPEN, i.e a cell can not
    be SHUT before it has been OPEN. This means that any cells that are always SHUT
    will not be included in the export.
    """

    eclsum = EclSum(str(filename), include_restart=False, lazy_load=False)
    column_names: Set[str] = set(EclSumKeyWordVector(eclsum, add_keywords=True))
    np_dates_ms = eclsum.numpy_dates

    cpi_columns = [
        col
        for col in column_names
        if re.match("^CPI:[A-Z0-9_-]{1,8}:[0-9]+,[0-9]+,[0-9]+$", col)
    ]
    df = pd.DataFrame(columns=["DATE", "WELL", "I", "J", "K", "OP/SH"])

    for col in cpi_columns:
        colsplit = col.split(":")
        well = colsplit[1]
        i, j, k = colsplit[2].split(",")

        vector = eclsum.numpy_vector(col)

        status_changes = _get_status_changes(np_dates_ms, vector)
        for date, status in status_changes:
            df.loc[df.shape[0]] = [date, well, i, j, k, status]

    return df


def main() -> None:
    """Entry point from command line"""
    parser = _get_parser()
    args = parser.parse_args()

    df = _extract_well_connection_status(args.eclbase.with_suffix(".UNSMRY"))

    # Create the output folder if it doesn't exist
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Write to file
    df.to_parquet(args.output, index=False)


if __name__ == "__main__":
    main()
