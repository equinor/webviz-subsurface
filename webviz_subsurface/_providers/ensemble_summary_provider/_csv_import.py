import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from webviz_subsurface._utils.perf_timer import PerfTimer

LOGGER = logging.getLogger(__name__)


def load_ensemble_summary_csv_file(
    csv_file: Path, ensemble_filter: Optional[str]
) -> pd.DataFrame:
    LOGGER.debug(f"load_ensemble_summary_csv_file() starting - {csv_file}")
    timer = PerfTimer()

    df: pd.DataFrame = pd.read_csv(csv_file)

    if ensemble_filter is not None:
        if "ENSEMBLE" not in df.columns:
            raise ValueError(
                "Cannot filter on ensemble, no ENSEMBLE column exist in CSV file"
            )

        df = df[df["ENSEMBLE"] == ensemble_filter]

    if "ENSEMBLE" in df.columns:
        if df["ENSEMBLE"].nunique() > 1:
            raise KeyError("Input data contains more than one unique ensemble name")

        df = df.drop(columns="ENSEMBLE")

    LOGGER.debug(
        f"load_ensemble_summary_csv_file() finished in: {timer.elapsed_s():.2f}s"
    )

    return df
