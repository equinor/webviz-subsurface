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
from typing import List, Tuple, Any
from pathlib import Path

import pandas as pd

DESCRIPTION = """
Export connection status data on sparse form from CPI summary data.
"""
CATEGORY = "utility.eclipse"
EXAMPLES: str = """
Extracts connection status history from summary parquet file by running
this in the ert workflow:

    FORWARD_MODEL EXPORT_CONNECTION_STATUS(<INPUT>=share/results/tables/summary.parquet, <OUTPUT>=share/results/tables/connection_status.parquet)

"""  # noqa


def _get_parser() -> argparse.ArgumentParser:
    """Setup parser for command line options"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=DESCRIPTION,
    )
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        help="Input file",
        default=Path("share/results/tables") / "summary.parquet",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output file",
        default=Path("share/results/tables") / "connection_status.parquet",
    )
    return parser


def _get_status_changes(
    df_conn: pd.DataFrame, cpi_column: str
) -> List[Tuple[Any, str]]:
    """Extracts the status history of a single connection as a list of tuples
    on the form (date, status)
    """
    status_changes = []
    prev_value = 0
    for _, row in df_conn.sort_values(by="DATE").iterrows():
        value = row[cpi_column]
        if value > 0 and prev_value == 0:
            status_changes.append((row.DATE, "OPEN"))
        elif prev_value > 0 and value == 0:
            status_changes.append((row.DATE, "SHUT"))
        prev_value = value
    return status_changes


def _extract_connection_status(filename: str) -> pd.DataFrame:
    """Exctracts connection status history for each compdat connection that
    is included in the summary data on the form CPI:WELL,I,J,K.

    From the CPI time series it is possible to extract the status of the connection
    because it is 0 when the connection is SHUT and >0 when the connection is open.

    The output from this function is one row for every time a connection changes
    status. The earliest date for any connection will be OPEN, i.e a cell can not
    be SHUT before it has been OPEN. This means that any cells that are always SHUT
    will not be included in the export.
    """
    smry = pd.read_parquet(filename)
    cpi_columns = [
        col
        for col in smry.columns
        if re.match("^CPI:[A-Z0-9_-]{1,8}:[0-9]+,[0-9]+,[0-9]+$", col)
    ]
    df = pd.DataFrame(columns=["DATE", "WELL", "I", "J", "K", "OP/SH"])

    for col in cpi_columns:
        colsplit = col.split(":")
        well = colsplit[1]
        coord = colsplit[2].split(",")
        i, j, k = coord[0], coord[1], coord[2]

        status_changes = _get_status_changes(smry[["DATE", col]], col)
        for date, status in status_changes:
            df.loc[df.shape[0]] = [date, well, i, j, k, status]

    return df


def main() -> None:
    """Entry point from command line"""
    parser = _get_parser()
    args = parser.parse_args()

    df = _extract_connection_status(args.input)
    df.to_parquet(args.output, index=False)


if __name__ == "__main__":
    main()
