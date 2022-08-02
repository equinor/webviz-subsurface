from typing import Dict, List, Optional, Tuple, Union

import webviz_core_components as wcc
from dash import Input, Output, callback, dcc
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC, ViewABC

from .._shared_settings import CaseSettings, FilterSettings
from .._supporting_files._plot_functions import (
    update_errorbarplot,
    update_errorbarplot_superimpose,
)


class ErrorbarPlotOptions(SettingsGroupABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        COLOR_BY = "color-br"
        SIM_ERRORBAR = "sim-errorbar"
        OBS_ERRORBAR = "obs-errorbar"

    def __init__(self) -> None:
        super().__init__("Plot options")

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Color by",
                id=self.register_component_unique_id(self.Ids.COLOR_BY),
                options=[
                    {
                        "label": "none",
                        "value": None,
                    },
                    {
                        "label": "region",
                        "value": "region",
                    },
                    {
                        "label": "sim_std",
                        "value": "sim_std",
                    },
                    {
                        "label": "diff_mean",
                        "value": "diff_mean",
                    },
                    {
                        "label": "diff_std",
                        "value": "diff_std",
                    },
                ],
                style={"display": "block"},
                value="region",
                clearable=False,
                persistence=True,
                persistence_type="memory",
            ),
            wcc.Dropdown(
                label="Sim errorbar",
                id=self.register_component_unique_id(self.Ids.SIM_ERRORBAR),
                options=[
                    {
                        "label": "Sim std",
                        "value": "sim_std",
                    },
                    {
                        "label": "Sim p10/p90",
                        "value": "sim_p10_p90",
                    },
                    {
                        "label": "none",
                        "value": None,
                    },
                ],
                value="sim_std",
                clearable=True,
                persistence=True,
                persistence_type="memory",
            ),
            wcc.Dropdown(
                label="Obs errorbar",
                id=self.register_component_unique_id(self.Ids.OBS_ERRORBAR),
                options=[
                    {
                        "label": "Obs std",
                        "value": "obs_error",
                    },
                    {
                        "label": "none",
                        "value": None,
                    },
                ],
                value=None,
            ),
        ]


class ErrorbarPlotSettingsAndLayout(SettingsGroupABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        LAYOUT_HEIGHT = "layout-height"
        LAYOUT_COLUMNS = "layout-columns"
        X_AXIS_SETTINGS = "x-axix-settings"
        SUPERIMPOSE_PLOT = "superimpose-plot"

    def __init__(self) -> None:
        super().__init__("Plot settings and layout")

    def layout(self) -> List[Component]:
        return [
            wcc.RadioItems(
                id=self.register_component_unique_id(self.Ids.X_AXIS_SETTINGS),
                label="X-axis settings",
                options=[
                    {
                        "label": "Reset index/sort by region",
                        "value": True,
                    },
                    {
                        "label": "Original ordering",
                        "value": False,
                    },
                ],
                value=False,
            ),
            wcc.RadioItems(
                label="Superimpose plots",
                id=self.register_component_unique_id(self.Ids.SUPERIMPOSE_PLOT),
                options=[
                    {
                        "label": "True",
                        "value": True,
                    },
                    {
                        "label": "False",
                        "value": False,
                    },
                ],
                value=False,
            ),
            wcc.Dropdown(
                label="Fig layout - height",
                id=self.register_component_unique_id(self.Ids.LAYOUT_HEIGHT),
                options=[
                    {
                        "label": "Very small",
                        "value": 250,
                    },
                    {
                        "label": "Small",
                        "value": 350,
                    },
                    {
                        "label": "Medium",
                        "value": 450,
                    },
                    {
                        "label": "Large",
                        "value": 700,
                    },
                    {
                        "label": "Very large",
                        "value": 1000,
                    },
                ],
                value=450,
                clearable=False,
                persistence=True,
                persistence_type="memory",
            ),
            wcc.Dropdown(
                label="Fig layout - # columns",
                id=self.register_component_unique_id(self.Ids.LAYOUT_COLUMNS),
                options=[
                    {
                        "label": "One column",
                        "value": 1,
                    },
                    {
                        "label": "Two columns",
                        "value": 2,
                    },
                    {
                        "label": "Three columns",
                        "value": 3,
                    },
                ],
                style={"display": "block"},
                value=1,
                clearable=False,
                persistence=True,
                persistence_type="memory",
            ),
        ]


class ErrorbarPlots(ViewABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        CASE_SETTINGS = "case-setting"
        FILTER_SETTINGS = "filter-settings"
        PLOT_OPTIONS = "misfit-options"
        PLOT_SETTINGS_AND_LAYOUT = "plot-settings-and-layout"
        GRAPHS = "graphs"

    def __init__(
        self,
        attributes: List[str],
        ens_names: List,
        region_names: List[int],
        realizations: List,
        dframe: Dict,
        caseinfo: str,
    ) -> None:
        super().__init__("Errorbar - sim vs obs")
        self.attributes = attributes
        self.ens_names = ens_names
        self.region_names = region_names
        self.realizations = realizations
        self.dframe = dframe
        self.caseinfo = caseinfo

        self.add_settings_groups(
            {
                self.Ids.CASE_SETTINGS: CaseSettings(self.attributes, self.ens_names),
                self.Ids.FILTER_SETTINGS: FilterSettings(
                    self.region_names, self.realizations
                ),
                self.Ids.PLOT_OPTIONS: ErrorbarPlotOptions(),
                self.Ids.PLOT_SETTINGS_AND_LAYOUT: ErrorbarPlotSettingsAndLayout(),
            }
        )

        self.add_column(self.Ids.GRAPHS)

    def set_callbacks(self) -> None:
        # --- Seismic errorbar plot - sim vs obs ---
        @callback(
            Output(
                self.layout_element(self.Ids.GRAPHS).get_unique_id().to_string(),
                "children",
            ),
            Output(
                self.settings_group(self.Ids.PLOT_SETTINGS_AND_LAYOUT)
                .component_unique_id(ErrorbarPlotSettingsAndLayout.Ids.LAYOUT_COLUMNS)
                .to_string(),
                "style",
            ),
            Output(
                self.settings_group(self.Ids.PLOT_OPTIONS)
                .component_unique_id(ErrorbarPlotOptions.Ids.COLOR_BY)
                .to_string(),
                "style",
            ),
            Input(
                self.settings_group(self.Ids.CASE_SETTINGS)
                .component_unique_id(CaseSettings.Ids.ATTRIBUTE_NAME)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.CASE_SETTINGS)
                .component_unique_id(CaseSettings.Ids.ENSEMBLES_NAME)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.FILTER_SETTINGS)
                .component_unique_id(FilterSettings.Ids.REGION_SELECTOR)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.FILTER_SETTINGS)
                .component_unique_id(FilterSettings.Ids.REALIZATION_SELECTOR)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.PLOT_OPTIONS)
                .component_unique_id(ErrorbarPlotOptions.Ids.COLOR_BY)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.PLOT_OPTIONS)
                .component_unique_id(ErrorbarPlotOptions.Ids.SIM_ERRORBAR)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.PLOT_OPTIONS)
                .component_unique_id(ErrorbarPlotOptions.Ids.OBS_ERRORBAR)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.PLOT_SETTINGS_AND_LAYOUT)
                .component_unique_id(ErrorbarPlotSettingsAndLayout.Ids.X_AXIS_SETTINGS)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.PLOT_SETTINGS_AND_LAYOUT)
                .component_unique_id(ErrorbarPlotSettingsAndLayout.Ids.SUPERIMPOSE_PLOT)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.PLOT_SETTINGS_AND_LAYOUT)
                .component_unique_id(ErrorbarPlotSettingsAndLayout.Ids.LAYOUT_COLUMNS)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.PLOT_SETTINGS_AND_LAYOUT)
                .component_unique_id(ErrorbarPlotSettingsAndLayout.Ids.LAYOUT_HEIGHT)
                .to_string(),
                "value",
            ),
            # prevent_initial_call=True,
        )
        # pylint: disable=too-many-arguments
        def _update_errorbar_graph(
            attr_name: str,
            ens_names: List[str],
            regions: List[Union[int, str]],
            realizations: List[Union[int, str]],
            colorby: Optional[str],
            errbar: Optional[str],
            errbarobs: Optional[str],
            resetindex: bool,
            superimpose: bool,
            figcols: int,
            figheight: int,
        ) -> Tuple:

            if not regions:
                raise PreventUpdate
            if not realizations:
                raise PreventUpdate

            # --- ensure int type
            regions = [int(reg) for reg in regions]
            realizations = [int(real) for real in realizations]

            # --- apply region filter
            dframe = self.dframe[attr_name].loc[
                self.dframe[attr_name]["region"].isin(regions)
            ]
            # --- apply realization filter
            col_names = ["real-" + str(real) for real in realizations]
            dframe = dframe.drop(
                columns=[
                    col for col in dframe if "real-" in col and col not in col_names
                ]
            )

            show_hide_selector = {"display": "block"}
            if superimpose:
                show_hide_selector = {"display": "none"}

            # --- apply ensemble filter
            dframe = dframe[dframe.ENSEMBLE.isin(ens_names)]

            # --- make graphs
            if superimpose:
                figures = update_errorbarplot_superimpose(
                    dframe,
                    showerrorbar=errbar,
                    showerrorbarobs=errbarobs,
                    reset_index=resetindex,
                    figheight=figheight,
                )
            else:
                figures = update_errorbarplot(
                    dframe,
                    colorby=colorby,
                    showerrorbar=errbar,
                    showerrorbarobs=errbarobs,
                    reset_index=resetindex,
                    fig_columns=figcols,
                    figheight=figheight,
                )
            if figures is None:
                figures = []

            return (
                figures
                + [
                    wcc.Selectors(
                        label="Ensemble info",
                        children=[
                            dcc.Textarea(
                                value=self.caseinfo,
                                style={
                                    "width": 500,
                                },
                            ),
                        ],
                    )
                ],
                show_hide_selector,
                show_hide_selector,
            )
