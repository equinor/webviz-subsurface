#!/usr/bin/env python
"""Batch conversion of UNSMRY files to Apache Arrow IPC file format
"""

import argparse
import glob
import logging
import os
import warnings
from pathlib import Path
from typing import List

import ecl2df

logger = logging.getLogger(__name__)


def _get_parser() -> argparse.ArgumentParser:
    """Setup parser for command line options"""

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.description = (
        "Batch conversion of UNSMRY files to Apache Arrow IPC file format.\n"
        "\n"
        "Required input is a path/paths which may be wildcarded, like:\n"
        "  smry2arrow_batch my_folder/realization-*/iter-0\n"
        "You may also define a specific file pattern for the UNSMRY file to read."
    )

    parser.add_argument(
        "enspath",
        type=Path,
        help="Path with wildcards giving file system location of the ensemble's realizations",
        nargs="*",
    )
    parser.add_argument(
        "--eclbase",
        type=Path,
        help='Eclipse base name, note that "" is required around paths with wildcards',
        default=Path("eclipse/model/*.UNSMRY"),
    )
    return parser


def _convert_single_smry_file(smry_filename: str, arrow_filename: str) -> None:
    """Read summary data for single realization from disk and write it out to .arrow
    file using ecl2df.
    """

    eclbase = (
        smry_filename.replace(".DATA", "").replace(".UNSMRY", "").replace(".SMSPEC", "")
    )

    eclfiles = ecl2df.EclFiles(eclbase)
    sum_df = ecl2df.summary.df(eclfiles)

    # Slight hack here, using ecl2df protected function to gain access to conversion routine
    # pylint: disable=protected-access
    sum_table = ecl2df.summary._df2pyarrow(sum_df)

    ecl2df.summary.write_dframe_stdout_file(sum_table, arrow_filename)


def _batch_convert_smry2arrow(
    ens_path: List[Path], ecl_base: Path, relative_output_dir: Path
) -> None:
    """Does batch conversion of UNSMRY files for all realizations within an ensemble."""

    for wildcarded_path in ens_path:
        globbed_real_dirs = sorted(glob.glob(str(wildcarded_path)))

        for real_dir in globbed_real_dirs:
            glob_expr = str(Path(real_dir) / ecl_base)
            globbed_smry_files = sorted(glob.glob(glob_expr))
            if globbed_smry_files:
                real_output_dir = Path(real_dir) / relative_output_dir
                real_output_dir.mkdir(parents=True, exist_ok=True)

                for smry_file in globbed_smry_files:
                    basename_without_ext = Path(Path(smry_file).name).stem
                    arrow_file = real_output_dir / (basename_without_ext + ".arrow")

                    logger.info(f"input(smry):   {smry_file}")
                    logger.info(f"output(arrow): {arrow_file}")
                    _convert_single_smry_file(smry_file, str(arrow_file))


def main() -> None:
    """Entry point from command line"""

    parser = _get_parser()
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    logger.setLevel(logging.INFO)

    enspath = args.enspath

    # Strip out any leading path separator from eclbase
    eclbase = str(args.eclbase).lstrip(os.path.sep)

    # If no extension has been given, we add .UNSMRY
    if not os.path.splitext(eclbase)[1]:
        eclbase += ".UNSMRY"

    # Output directory relative to each realization's root directory
    relative_output_dir = Path("share/results/unsmry")

    warnings.warn(
        "This script is a temporary solution for converting existing ensemble summary data "
        "for usage with webviz-subsurface, and will probably be removed in the future. "
        "New ensembles should be configured with an ert job for outputting .arrow files directly.",
        FutureWarning,
    )

    logger.info(f"enspath: {enspath}")
    logger.info(f"eclbase: {eclbase}")

    _batch_convert_smry2arrow(enspath, Path(eclbase), relative_output_dir)

    logger.info("done")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()
