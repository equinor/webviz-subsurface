import json
from pathlib import Path
from typing import Callable, Dict, List, Tuple
from uuid import uuid4

import numpy as np
import pandas as pd
import webviz_subsurface_components as wsc
from dash import html
from scipy.stats import chi2
from webviz_config import WebvizPluginABC, WebvizSettings

from .._datainput.history_match import extract_mismatch


class HistoryMatch(WebvizPluginABC):
    """Visualizes the quality of the history match.

---

* **`ensembles`:** List of the ensembles in `shared_settings` to visualize.
* **`observation_file`:** Path to the observation `.yaml` file \
(absolute or relative to config file).

---
Parameter values are extracted automatically from the `parameters.txt` files
of the individual realizations of your given `ensembles`, using the `fmu-ensemble` library.

?> The `observation_file` is a common (optional) file for all ensembles, which can be \
converted from e.g. ERT and ResInsight formats using the [fmuobs]\
(https://equinor.github.io/subscript/scripts/fmuobs.html) script. \
[An example of the format can be found here]\
(https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_history_match/share/\
observations/observations.yml).
"""

    def __init__(
        self,
        webviz_settings: WebvizSettings,
        ensembles: List[str],
        observation_file: Path,
    ):

        super().__init__()

        self.observation_file = observation_file

        self.ensembles = ensembles
        self.ens_paths = {
            ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
            for ens in ensembles
        }

        data = extract_mismatch(self.ens_paths, self.observation_file)
        self.hm_data = json.dumps(self._prepare_data(data))

        self.hm_id = f"hm-id-{uuid4()}"

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        return [
            (
                extract_mismatch,
                [
                    {
                        "ens_paths": self.ens_paths,
                        "observation_file": self.observation_file,
                    }
                ],
            )
        ]

    def _prepare_data(self, data: pd.DataFrame) -> dict:
        data = data.copy().reset_index()

        num_obs_groups = len(data.obs_group_name.unique())

        data["avg_pos"] = data["total_pos"] / data["number_data_points"]
        data["avg_neg"] = data["total_neg"] / data["number_data_points"]

        iterations = []
        for ensemble in self.ensembles:
            df = data[data.ensemble_name == ensemble]
            iterations.append(df.groupby("obs_group_name").mean())

        sorted_iterations = HistoryMatch._sort_iterations(iterations)

        iterations_dict = HistoryMatch._iterations_to_dict(
            sorted_iterations, self.ensembles
        )

        confidence_sorted = _get_sorted_edges(num_obs_groups)
        confidence_unsorted = _get_unsorted_edges()

        data = {}
        data["iterations"] = iterations_dict
        data["confidence_interval_sorted"] = confidence_sorted
        data["confidence_interval_unsorted"] = confidence_unsorted

        return data

    @staticmethod
    def _sort_iterations(iterations: List[pd.DataFrame]) -> List[pd.DataFrame]:
        sorted_data = []

        for df in iterations:
            sorted_df = df.copy()

            sorted_data.append(
                sorted_df.assign(f=sorted_df["avg_pos"] + sorted_df["avg_neg"])
                .sort_values("f", ascending=False)
                .drop("f", axis=1)
            )

        return sorted_data

    @staticmethod
    def _iterations_to_dict(
        iterations: List[pd.DataFrame], labels: List[str]
    ) -> List[dict]:
        retval = []

        for iteration, label in zip(iterations, labels):
            retval.append(
                {
                    "name": label,
                    "positive": iteration["avg_pos"].tolist(),
                    "negative": iteration["avg_neg"].tolist(),
                    "labels": iteration.index.tolist(),
                }
            )

        return retval

    @property
    def layout(self) -> html.Div:
        return html.Div([wsc.HistoryMatch(id=self.hm_id, data=self.hm_data)])


def _get_unsorted_edges() -> dict:
    """P10 - P90 unsorted edge coordinates"""

    retval = {"low": chi2.ppf(0.1, 1), "high": chi2.ppf(0.9, 1)}

    return retval


def _get_sorted_edges(number_observation_groups: int) -> Dict[str, list]:
    """P10 - P90 sorted edge coordinates"""

    monte_carlo_iterations = 100000

    sorted_values = np.empty((number_observation_groups, monte_carlo_iterations))

    for i in range(monte_carlo_iterations):
        sorted_values[:, i] = np.sort(
            np.random.chisquare(df=1, size=number_observation_groups)
        )

    sorted_values = np.flip(sorted_values, 0)

    p10 = np.percentile(sorted_values, 90, axis=1)
    p90 = np.percentile(sorted_values, 10, axis=1)

    # Dictionary with two arrays (P10, P90). Each array of length equal
    # to number of observation groups i.e. number of items along y axis.
    # These values are to be used for drawing the stair stepped
    # sorted P10-P90 area:

    coordinates = {"low": list(p10), "high": list(p90)}

    return coordinates
