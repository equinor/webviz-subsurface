#!/usr/bin/env python
"""Batch conversion of UNSMRY files to Apache Arrow IPC file format
"""

import argparse
import glob
import logging
import os
from pathlib import Path

from .smry2arrow import smry2arrow

logger = logging.getLogger(__name__)


def _get_parser() -> argparse.ArgumentParser:
    """Setup parser for command line options"""

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.description = (
        "Batch conversion of UNSMRY files to Apache Arrow IPC file format.\n"
        "\n"
        "Note that if the enspath argument includes wildcards you will have to enclose it\n"
        "in quotes to stop the shell from expanding it, e.g.:\n"
        '  smry2arrow_batch "my_folder/realization-*/iter-0"'
    )

    parser.add_argument(
        "enspath",
        type=Path,
        help="Path with wildcards giving file system location of the ensemble's realizations",
    )
    parser.add_argument(
        "--eclbase",
        type=Path,
        help="Eclipse base name",
        default=Path("eclipse/model/*.UNSMRY"),
    )
    return parser


def _batch_convert_smry2arrow(
    ens_path: Path, ecl_base: Path, relative_output_dir: Path
) -> None:
    """Does batch conversion of UNSMRY files for all realizations within an ensemble."""
    globbed_real_dirs = sorted(glob.glob(str(ens_path)))

    for real_dir in globbed_real_dirs:
        glob_expr = os.path.join(real_dir, ecl_base)
        globbed_smry_files = sorted(glob.glob(glob_expr))
        if globbed_smry_files:
            real_output_dir = os.path.join(real_dir, relative_output_dir)
            os.makedirs(real_output_dir, exist_ok=True)

            for smry_file in globbed_smry_files:
                basename_without_ext = os.path.basename(os.path.splitext(smry_file)[0])
                arrow_file = os.path.join(
                    real_output_dir, basename_without_ext + ".arrow"
                )

                logger.info(f"input(smry):   {smry_file}")
                logger.info(f"output(arrow): {arrow_file}")

                smry2arrow(Path(smry_file), Path(arrow_file))


def main() -> None:
    """Entry point from command line"""

    parser = _get_parser()
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    # logging.basicConfig(level=logging.DEBUG)
    # logger.debug(f"args.enspath: {args.enspath}")
    # logger.debug(f"args.eclbase: {args.eclbase}")

    enspath = args.enspath

    # Strip out any leading path separator from eclbase
    eclbase = str(args.eclbase).lstrip(os.path.sep)

    # If no extension has been given, we add .UNSMRY
    if not os.path.splitext(eclbase)[1]:
        eclbase += ".UNSMRY"

    # Output directory relative to each realization's root directory
    relative_output_dir = Path("share/results/unsmry")

    logger.info(f"enspath: {enspath}")
    logger.info(f"eclbase: {eclbase}")

    _batch_convert_smry2arrow(enspath, Path(eclbase), relative_output_dir)

    logger.info("done")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()
