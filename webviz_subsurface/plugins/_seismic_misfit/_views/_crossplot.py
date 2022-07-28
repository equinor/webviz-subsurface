from typing import Dict, List, Optional, Union

import webviz_core_components as wcc
from dash import Input, Output, callback, dcc
from dash.exceptions import PreventUpdate
from webviz_config.webviz_plugin_subclasses import ViewABC

from .._shared_settings import (
    CaseSettings,
    FilterSettings,
    PlotOptions,
    PlotSettingsAndLayout,
)
from .._supporting_files._plot_functions import update_crossplot


class Crossplot(ViewABC):
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
        super().__init__("Crossplot - sim vs obs")
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
                self.Ids.PLOT_OPTIONS: PlotOptions(),
                self.Ids.PLOT_SETTINGS_AND_LAYOUT: PlotSettingsAndLayout(),
            }
        )

        self.add_column(self.Ids.GRAPHS)

    def set_callbacks(self) -> None:
        # --- Seismic crossplot - sim vs obs ---
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
                self.settings_group(self.Ids.PLOT_OPTIONS)
                .component_unique_id(PlotOptions.Ids.COLOR_BY)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.PLOT_OPTIONS)
                .component_unique_id(PlotOptions.Ids.SIZE_BY)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.PLOT_OPTIONS)
                .component_unique_id(PlotOptions.Ids.SIM_ERROR_BAR)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.PLOT_SETTINGS_AND_LAYOUT)
                .component_unique_id(PlotSettingsAndLayout.Ids.LAYOUT_COLUMNS)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.PLOT_SETTINGS_AND_LAYOUT)
                .component_unique_id(PlotSettingsAndLayout.Ids.LAYOUT_HEIGHT)
                .to_string(),
                "value",
            ),
            # prevent_initial_call=True,
        )
        def _update_crossplot_graph(
            attr_name: str,
            ens_names: List[str],
            regions: List[Union[int, str]],
            realizations: List[Union[int, str]],
            colorby: Optional[str],
            sizeby: Optional[str],
            showerrbar: Optional[str],
            figcols: int,
            figheight: int,
        ) -> Optional[List[wcc.Graph]]:

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

            # --- apply ensemble filter
            dframe = dframe[dframe.ENSEMBLE.isin(ens_names)]

            # --- make graphs
            figures = update_crossplot(
                dframe,
                colorby=colorby,
                sizeby=sizeby,
                showerrorbar=showerrbar,
                fig_columns=figcols,
                figheight=figheight,
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
