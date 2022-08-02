import json
from typing import Callable, List, Optional, Tuple, Type, Union

import numpy as np
import pandas as pd
from dash import html
from dash.development.base_component import Component
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

from ..._datainput.fmu_input import load_ensemble_set, load_parameters
from ._plugin_ids import PluginIds
from ._shared_settings import RunningTimeAnalysisFmuSettings
from ._view import RunTimeAnalysisGraph


class RunningTimeAnalysisFMU(WebvizPluginABC):
    """Can e.g. be used to investigate which jobs that are important for the running
    time of realizations, and if specific parameter combinations increase running time or chance of
    realization failure. Systematic realization failure could introduce bias to assisted history
    matching.

    Visualizations:
    * Running time matrix, a heatmap of job running times relative to:
        * Same job in ensemble
        * Slowest job in ensemble
        * Slowest job in realization
    * Parameter parallel coordinates plot:
        * Analyze running time and successful/failed run together with input parameters.

    ---

    * **`ensembles`:** Which ensembles in `shared_settings` to include in check.
                       Only required input.
    * **`filter_shorter`:** Filters jobs with maximum run time in ensemble less than X seconds \
        (default: 10). Can be checked on/off interactively, this only sets the filtering value.
    * **`status_file`:** Name of json file local per realization with job status \
        (default: `status.json`).
    * **`visual_parameters`:** List of default visualized parameteres in parallel coordinates plot \
        (default: all parameters).

    ---

    Parameters are picked up automatically from `parameters.txt` in individual realizations in
    defined ensembles using `fmu-ensemble`.

    The `status.json` file is the standard status file when running
    [`ERT`](https://github.com/Equinor/ert) runs. If defining a different name, it still has to be
    on the same format [(example file)](https://github.com/equinor/webviz-subsurface-testdata/\
    blob/master/reek_history_match/realization-0/iter-0/status.json).
    """

    def __init__(
        self,
        webviz_settings: WebvizSettings,
        ensembles: list,
        filter_shorter: Union[int, float] = 10,
        status_file: str = "status.json",
        visual_parameters: Optional[list] = None,
    ) -> None:
        super().__init__(stretch=True)
        self.filter_shorter = filter_shorter
        self.ens_paths = {
            ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
            for ens in ensembles
        }

        self.plotly_theme = webviz_settings.theme.plotly_theme
        self.ensembles = ensembles
        self.status_file = status_file
        self.parameter_df = load_parameters(
            ensemble_paths=self.ens_paths,
            ensemble_set_name="EnsembleSet",
            filter_file=None,
        )
        all_data_df = make_status_df(
            self.ens_paths, self.status_file
        )  # Has to be stored in one df due to webvizstore, see issue #206 in webviz-config
        self.job_status_df = all_data_df.loc["job"]
        self.real_status_df = all_data_df.loc["real"]
        self.visual_parameters = (
            visual_parameters if visual_parameters else self.parameters
        )
        self.plugin_parameters = self.parameters

        self.add_store(
            PluginIds.Stores.VIEW_ELEMENT_HEIGHT, WebvizPluginABC.StorageType.SESSION
        )

        self.add_view(
            RunTimeAnalysisGraph(
                self.plotly_theme,
                self.job_status_df,
                self.real_status_df,
                self.ensembles,
                self.visual_parameters,
                self.plugin_parameters,
                self.filter_shorter,
            ),
            PluginIds.RunTimeAnalysisView.RUN_TIME_FMU,
            PluginIds.RunTimeAnalysisView.GROUP_NAME,
        )

    @property
    def layout(self) -> Type[Component]:
        return html.Div("No view is loaded.")

    @property
    def tour_steps(self) -> List[dict]:
        return [
            {
                "id": self.view(PluginIds.RunTimeAnalysisView.RUN_TIME_FMU)
                .settings_group(RunTimeAnalysisGraph.Ids.RUN_TIME_SETTINGS)
                .component_unique_id(RunningTimeAnalysisFmuSettings.Ids.MODE),
                "content": (
                    "Switch between job running time matrix and parameter parallel coordinates."
                ),
            },
            {
                "id": self.view(PluginIds.RunTimeAnalysisView.RUN_TIME_FMU)
                .settings_group(RunTimeAnalysisGraph.Ids.RUN_TIME_SETTINGS)
                .component_unique_id(RunningTimeAnalysisFmuSettings.Ids.ENSEMBLE),
                "content": ("Display the realizations from the selected ensemble. "),
            },
            {
                "id": self.view(PluginIds.RunTimeAnalysisView.RUN_TIME_FMU)
                .settings_group(RunTimeAnalysisGraph.Ids.RUN_TIME_SETTINGS)
                .component_unique_id(RunningTimeAnalysisFmuSettings.Ids.COLORING),
                "content": ("Make the colorscale relative to the selected option."),
            },
        ]

    @property
    def parameters(self) -> List[str]:
        """Returns numerical input parameters"""
        return list(
            self.parameter_df.drop(["ENSEMBLE", "REAL"], axis=1)
            .apply(pd.to_numeric, errors="coerce")
            .dropna(how="all", axis="columns")
            .columns
        )

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        return [
            (
                make_status_df,
                [
                    {
                        "ens_paths": self.ens_paths,
                        "status_file": self.status_file,
                    }
                ],
            ),
            (
                load_parameters,
                [
                    {
                        "ensemble_paths": self.ens_paths,
                        "filter_file": None,
                    },
                ],
            ),
        ]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
# pylint: disable=too-many-locals
# pylint: disable=too-many-statements
def make_status_df(
    ens_paths: dict,
    status_file: str,
) -> pd.DataFrame:
    """Return DataFrame of information from status.json files.
    *Finds status.json filepaths.
    For jobs:
    *Loads data into pandas DataFrames.
    *Calculates runtimes and normalized runtimes.
    *Creates hoverinfo column to be used in visualization.
    For realizations:
    *Creates DataFrame of success/failure and total running time.
    """

    parameter_df = load_parameters(
        ensemble_paths=ens_paths,
        ensemble_set_name="EnsembleSet",
        filter_file=None,
    )
    # sub-method to process ensemble data when all realizations in ensemble have been processed
    def ensemble_post_processing() -> list:
        # add missing realizations to get whitespace in heatmap matrix
        if len(set(range(min(reals), max(reals) + 1))) > len(set(reals)):
            missing_df = ens_dfs[0].copy()
            missing_df["STATUS"] = "Realization not started"
            missing_df["RUNTIME"] = np.NaN
            missing_df["JOB_SCALED_RUNTIME"] = np.NaN
            missing_df["ENS_SCALED_RUNTIME"] = np.NaN
            for missing_real in set(range(min(reals), max(reals) + 1)).difference(
                set(reals)
            ):
                ens_dfs.append(missing_df.copy())
                ens_dfs[-1]["REAL"] = missing_real
                ens_dfs[-1]["ENSEMBLE"] = ens
        # Concatenate realization DataFrames to an Ensemble DataFrame and store in list
        job_status_dfs.append(pd.concat(ens_dfs))
        # Find max running time of job in ensemble and create scaled columns
        job_status_dfs[-1]["JOB_MAX_RUNTIME"] = pd.concat(
            [ens_max_job_runtime] * (len(ens_dfs))
        )
        job_status_dfs[-1]["JOB_SCALED_RUNTIME"] = (
            job_status_dfs[-1]["RUNTIME"] / job_status_dfs[-1]["JOB_MAX_RUNTIME"]
        )
        job_status_dfs[-1]["ENS_SCALED_RUNTIME"] = job_status_dfs[-1][
            "RUNTIME"
        ] / np.amax(ens_max_job_runtime)
        # Return ensemble DataFrame list updated with the latest ensemble
        return job_status_dfs

    # find status filepaths
    ens_set = load_ensemble_set(ens_paths, filter_file=None)
    df = pd.concat(
        [
            ens_set[ens].find_files(status_file).assign(ENSEMBLE=ens)
            for ens in ens_set.ensemblenames
        ]
    )
    # Initial values for local variables
    job_status_dfs: list = []
    ens_dfs: list = []
    real_status: list = []
    ens_max_job_runtime = 1
    ens = ""
    reals: list = []

    # Loop through identified filepaths and get realization data
    for row in df.itertuples(index=False):
        # Load each json-file to a DataFrame for the realization
        with open(row.FULLPATH) as fjson:
            status_dict = json.load(fjson)
        real_df = pd.DataFrame(status_dict["jobs"])

        # If new ensemble, calculate ensemble scaled runtimes
        # for previous ensemble and reset temporary ensemble data
        if ens != row.ENSEMBLE:
            if ens == "":  # First ensemble
                ens = row.ENSEMBLE
            else:  # Store last ensemble and reset temporary ensemble data
                job_status_dfs = ensemble_post_processing()
                ens_max_job_runtime = 1
                ens_dfs = []
                ens = row.ENSEMBLE
                reals = []

        # Additional realization data into realization DataFrame
        real_df["RUNTIME"] = real_df["end_time"] - real_df["start_time"]
        real_df["REAL"] = row.REAL
        real_df["ENSEMBLE"] = row.ENSEMBLE
        real_df["REAL_SCALED_RUNTIME"] = real_df["RUNTIME"] / max(
            real_df["RUNTIME"].dropna()
        )
        real_df = real_df[
            ["ENSEMBLE", "REAL", "RUNTIME", "REAL_SCALED_RUNTIME", "name", "status"]
        ].rename(columns={"name": "JOB", "status": "STATUS"})
        # Status DataFrame to be used with parallel coordinates
        if all(real_df["STATUS"] == "Success"):
            real_status.append(
                {
                    "ENSEMBLE": row.ENSEMBLE,
                    "REAL": row.REAL,
                    "STATUS": "Success",
                    "STATUS_BOOL": 1,
                    "RUNTIME": status_dict["end_time"] - status_dict["start_time"],
                }
            )
        else:
            real_status.append(
                {
                    "ENSEMBLE": row.ENSEMBLE,
                    "REAL": row.REAL,
                    "STATUS": "Failure",
                    "STATUS_BOOL": 0,
                    "RUNTIME": None,
                }
            )

        # Need unique job ids names to separate jobs in same realization with same name in json file
        real_df["JOB_ID"] = range(0, len(real_df["JOB"]))

        # Update max runtime for jobs in ensemble
        ens_max_job_runtime = np.fmax(real_df["RUNTIME"], ens_max_job_runtime)

        # Append realization to ensemble data
        reals.append(row.REAL)
        ens_dfs.append(real_df)

    # Add last ensemble
    job_status_dfs = ensemble_post_processing()
    job_status_df = pd.concat(job_status_dfs, sort=False)

    # Create hoverinfo
    job_status_df["HOVERINFO"] = (
        "Real: "
        + job_status_df["REAL"].astype(str)
        + "<br>"
        + "Job: #"
        + job_status_df["JOB_ID"].astype(str)
        + "<br>"
        + job_status_df["JOB"].astype(str)
        + "<br>"
        + "Running time: "
        + job_status_df["RUNTIME"].astype(str)
        + " s"
        + "<br>"
        + "Status: "
        + job_status_df["STATUS"]
    )
    # Create dataframe of realization status and merge with realization parameters for parameter
    # parallel coordinates
    real_status_df = pd.DataFrame(real_status).merge(
        parameter_df, on=["ENSEMBLE", "REAL"]
    )
    # Has to be stored in one df due to webvizstore, see issue #206 in webviz-config
    return pd.concat([job_status_df, real_status_df], keys=["job", "real"], sort=False)
