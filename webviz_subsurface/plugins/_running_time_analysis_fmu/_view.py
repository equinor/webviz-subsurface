from typing import List, Union

import pandas as pd
import webviz_core_components as wcc
from dash import Input, Output, callback
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import ViewABC

from ._shared_settings import RunningTimeAnalysisFmuSettings
from ._view_elements import make_colormap, render_matrix, render_parcoord


class RunTimeAnalysisGraph(ViewABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        RUN_TIME_SETTINGS = "run-time-settings"
        RUNTIME_ANALYSIS = "run-time-analysis"

    def __init__(
        self,
        plotly_theme: dict,
        job_status_df: pd.DataFrame,
        real_status_df: pd.DataFrame,
        ensembles: list,
        visual_parameters: list,
        plugin_paratamters: List[str],
        filter_shorter: Union[int, float] = 10,
    ) -> None:
        super().__init__("Group tree")

        self.plotly_theme = plotly_theme
        self.job_status_df = job_status_df
        self.real_status_df = real_status_df
        self.filter_shorter = filter_shorter
        self.cooridinates_params = None
        self.ensembles = ensembles
        self.visual_parameters = visual_parameters
        self.plugin_parameters = plugin_paratamters

        self.add_column(self.Ids.RUNTIME_ANALYSIS)

        self.add_settings_group(
            RunningTimeAnalysisFmuSettings(
                self.real_status_df,
                self.ensembles,
                self.visual_parameters,
                self.plugin_parameters,
                self.filter_shorter,
            ),
            self.Ids.RUN_TIME_SETTINGS,
        )

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.layout_element(RunTimeAnalysisGraph.Ids.RUNTIME_ANALYSIS)
                .get_unique_id()
                .to_string(),
                "children",
            ),
            Input(
                self.settings_group(self.Ids.RUN_TIME_SETTINGS)
                .component_unique_id(RunningTimeAnalysisFmuSettings.Ids.MODE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.RUN_TIME_SETTINGS)
                .component_unique_id(RunningTimeAnalysisFmuSettings.Ids.ENSEMBLE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.RUN_TIME_SETTINGS)
                .component_unique_id(RunningTimeAnalysisFmuSettings.Ids.COLORING)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.RUN_TIME_SETTINGS)
                .component_unique_id(RunningTimeAnalysisFmuSettings.Ids.FILTER_SHORT)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.RUN_TIME_SETTINGS)
                .component_unique_id(RunningTimeAnalysisFmuSettings.Ids.FILTER_PARAMS)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.RUN_TIME_SETTINGS)
                .component_unique_id(RunningTimeAnalysisFmuSettings.Ids.REMOVE_CONSTANT)
                .to_string(),
                "value",
            ),
        )
        def _update_fig(
            mode: str,
            ens: str,
            coloring: str,
            filter_short: List[str],
            params: Union[str, List[str]],
            remove_constant: str,
        ) -> Component:
            """Update main figure
            Dependent on `mode` it will call rendering of the chosen form of visualization
            """
            plot_info = None

            if mode == "running_time_matrix":
                if "filter_short" in filter_short:
                    plot_info = render_matrix(
                        self.job_status_df[
                            (self.job_status_df["ENSEMBLE"] == ens)
                            & (
                                self.job_status_df["JOB_MAX_RUNTIME"]
                                >= self.filter_shorter
                            )
                        ],
                        coloring,
                        self.plotly_theme,
                    )
                else:
                    plot_info = render_matrix(
                        self.job_status_df[(self.job_status_df["ENSEMBLE"] == ens)],
                        coloring,
                        self.plotly_theme,
                    )

            else:
                # Otherwise: parallel coordinates
                # Ensure selected parameters is a list
                params = params if isinstance(params, list) else [params]
                # Color by success or runtime, for runtime drop unsuccesful
                colormap_labels: Union[List[str], None]
                if coloring == "Successful/failed realization":
                    plot_df = self.real_status_df[
                        self.real_status_df["ENSEMBLE"] == ens
                    ]
                    colormap = make_colormap(
                        self.plotly_theme["layout"]["colorway"], discrete=2
                    )
                    color_by_col = "STATUS_BOOL"
                    colormap_labels = ["Failed", "Success"]
                else:
                    plot_df = self.real_status_df[
                        (self.real_status_df["ENSEMBLE"] == ens)
                        & (self.real_status_df["STATUS_BOOL"] == 1)
                    ]
                    colormap = self.plotly_theme["layout"]["colorscale"]["sequential"]
                    color_by_col = "RUNTIME"
                    colormap_labels = None

                # Call rendering of parallel coordinate plot
                plot_info = render_parcoord(
                    plot_df,
                    params,
                    self.plotly_theme,
                    colormap,
                    color_by_col,
                    remove_constant,
                    colormap_labels,
                )
            return wcc.Graph(figure=plot_info)
