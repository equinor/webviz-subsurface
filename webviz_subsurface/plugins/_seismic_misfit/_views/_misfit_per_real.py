from typing import Dict, List, Union

import webviz_core_components as wcc
from dash import Input, Output, callback, dcc
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC, ViewABC

from .._shared_settings import CaseSettings, FilterSettings
from .._supporting_files._plot_functions import update_misfit_plot


class MisfitOptions(SettingsGroupABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        WEIGHT = "weight"
        EXPONENT = "exponent"
        NORMALIZATION = "normalization"

    def __init__(self) -> None:
        super().__init__("Misfit Options")

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Misfit weight",
                id=self.register_component_unique_id(self.Ids.WEIGHT),
                options=[
                    {
                        "label": "none",
                        "value": None,
                    },
                    {
                        "label": "Obs error",
                        "value": "obs_error",
                    },
                ],
                value="obs_error",
                clearable=False,
                persistence=True,
                persistence_type="memory",
            ),
            wcc.Dropdown(
                label="Misfit exponent",
                id=self.register_component_unique_id(self.Ids.EXPONENT),
                options=[
                    {
                        "label": "Linear sum",
                        "value": 1.0,
                    },
                    {
                        "label": "Squared sum",
                        "value": 2.0,
                    },
                ],
                value=2.0,
                clearable=False,
                persistence=True,
                persistence_type="memory",
            ),
            wcc.Dropdown(
                label="Misfit normalization",
                id=self.register_component_unique_id(self.Ids.NORMALIZATION),
                options=[
                    {
                        "label": "Yes",
                        "value": True,
                    },
                    {
                        "label": "No",
                        "value": False,
                    },
                ],
                value=False,
                clearable=False,
                persistence=True,
                persistence_type="memory",
            ),
        ]


class PerRealPlotSettingsAndLayout(SettingsGroupABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        SORTING = "sorting"
        HEIGHT = "height"

    def __init__(self) -> None:
        super().__init__("Plot settings and layout")

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Sorting/ranking",
                id=self.register_component_unique_id(self.Ids.SORTING),
                options=[
                    {
                        "label": "none",
                        "value": None,
                    },
                    {
                        "label": "ascending",
                        "value": True,
                    },
                    {
                        "label": "descending",
                        "value": False,
                    },
                ],
                value=True,
            ),
            wcc.Dropdown(
                label="Fig layout - height",
                id=self.register_component_unique_id(self.Ids.HEIGHT),
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
        ]


class MisfitPerReal(ViewABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        CASE_SETTINGS = "case-setting"
        FILTER_SETTINGS = "filter-settings"
        PLOT_SETTINGS_AND_LAYOUT = "plot-settings-and-layout"
        MISFIT_OPTIONS = "misfit-options"
        GRAPHS = "graphs"
        INFO_ELEMENT = "info-element"

    def __init__(
        self,
        attributes: List[str],
        ens_names: List,
        region_names: List[int],
        realizations: List,
        dframe: Dict,
        caseinfo: str,
    ) -> None:
        super().__init__("Misfit per real")
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
                self.Ids.PLOT_SETTINGS_AND_LAYOUT: PerRealPlotSettingsAndLayout(),
                self.Ids.MISFIT_OPTIONS: MisfitOptions(),
            }
        )

        self.add_column(self.Ids.GRAPHS)

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.layout_element(self.Ids.GRAPHS).get_unique_id().to_string(),
                "children",
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
                self.settings_group(self.Ids.PLOT_SETTINGS_AND_LAYOUT)
                .component_unique_id(PerRealPlotSettingsAndLayout.Ids.SORTING)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.PLOT_SETTINGS_AND_LAYOUT)
                .component_unique_id(PerRealPlotSettingsAndLayout.Ids.HEIGHT)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.MISFIT_OPTIONS)
                .component_unique_id(MisfitOptions.Ids.WEIGHT)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.MISFIT_OPTIONS)
                .component_unique_id(MisfitOptions.Ids.EXPONENT)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.MISFIT_OPTIONS)
                .component_unique_id(MisfitOptions.Ids.NORMALIZATION)
                .to_string(),
                "value",
            ),
            # prevent_initial_call=True,
        )
        # pylint: disable=too-many-arguments
        def _update_misfit_graph(
            attr_name: str,
            ens_names: List,
            regions: List[Union[int, str]],
            realizations: List[Union[int, str]],
            sorting: str,
            figheight: int,
            misfit_weight: str,
            misfit_exponent: float,
            misfit_normalization: bool,
        ) -> List:

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

            if not isinstance(ens_names, List):
                ens_names = [ens_names]

            # --- apply ensemble filter
            dframe = dframe[dframe.ENSEMBLE.isin(ens_names)]

            # --- make graphs, return as list
            figures = update_misfit_plot(
                dframe,
                sorting,
                figheight,
                misfit_weight,
                misfit_exponent,
                misfit_normalization,
            )

            return figures + [
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
            ]
