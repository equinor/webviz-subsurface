from typing import Dict, List, Tuple, Union

import pandas as pd
import webviz_core_components as wcc
from dash import Input, Output, callback
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from webviz_config import WebvizSettings
from webviz_config.webviz_plugin_subclasses import ViewABC

from .._plugin_ids import PluginIds
from ..shared_settings import Filter, ShowPlots
from ._view_funcions import create_graph, filter_data_frame


class PvtView(ViewABC):

    # pylint: disable=too-few-public-methods
    class Ids:
        PVT_GRAPHS = "formation-volume-factor"
        VISCOSITY = "viscosity"
        DENSITY = "density"
        GAS_OIL_RATIO = "gas-oil-ratio"

    PHASES = ["OIL", "GAS", "WATER"]

    def __init__(self, pvt_df: pd.DataFrame, webviz_settings: WebvizSettings) -> None:
        super().__init__("Pvt View")

        self.pvt_df = pvt_df
        self.plotly_theme = webviz_settings.theme.plotly_theme

        self.phases_additional_info: List[str] = []
        if self.pvt_df["KEYWORD"].str.contains("PVTO").any():
            self.phases_additional_info.append("PVTO")
        elif self.pvt_df["KEYWORD"].str.contains("PVDO").any():
            self.phases_additional_info.append("PVDO")
        elif self.pvt_df["KEYWORD"].str.contains("PVCDO").any():
            self.phases_additional_info.append("PVCDO")
        if self.pvt_df["KEYWORD"].str.contains("PVTG").any():
            self.phases_additional_info.append("PVTG")
        elif self.pvt_df["KEYWORD"].str.contains("PVDG").any():
            self.phases_additional_info.append("PVDG")
        if self.pvt_df["KEYWORD"].str.contains("PVTW").any():
            self.phases_additional_info.append("PVTW")

        self.add_settings_groups(
            {
                PluginIds.SharedSettings.FILTER: Filter(self.pvt_df),
                PluginIds.SharedSettings.SHOWPLOTS: ShowPlots(),
            }
        )

        self.add_column(PvtView.Ids.PVT_GRAPHS)

    @staticmethod
    def plot_visibility_options(phase: str = "") -> Dict[str, str]:
        options = {
            "fvf": "Formation Volume Factor",
            "viscosity": "Viscosity",
            "density": "Density",
            "ratio": "Gas/Oil Ratio (Rs)",
        }
        if phase == "PVTO":
            options["ratio"] = "Gas/Oil Ratio (Rs)"
        if phase == "PVTG":
            options["ratio"] = "Vaporized Oil Ratio (Rv)"
        if phase == "WATER":
            options.pop("ratio")
        return options

    @property
    def phases(self) -> Dict[str, str]:
        phase_descriptions: Dict[str, str] = {}
        for i, phase in enumerate(PvtView.PHASES):
            phase_descriptions[phase] = self.phases_additional_info[i]
        return phase_descriptions

    @property
    def ensembles(self) -> List[str]:
        return list(self.pvt_df["ENSEMBLE"].unique())

    @property
    def pvtnums(self) -> List[str]:
        return list(self.pvt_df["PVTNUM"].unique())

    @property
    def ensemble_colors(self) -> Dict[str, List[str]]:
        return {
            ensemble: self.plotly_theme["layout"]["colorway"][
                self.ensembles.index(ensemble)
            ]
            for ensemble in self.ensembles
        }

    @property
    def pvtnum_colors(self) -> Dict[str, List[str]]:
        return {
            pvtnum: self.plotly_theme["layout"]["colorway"][self.pvtnums.index(pvtnum)]
            for pvtnum in self.pvtnums
        }

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.settings_group(PluginIds.SharedSettings.SHOWPLOTS)
                .component_unique_id(ShowPlots.Ids.SHOWPLOTS)
                .to_string(),
                "options",
            ),
            Output(
                self.settings_group(PluginIds.SharedSettings.SHOWPLOTS)
                .component_unique_id(ShowPlots.Ids.SHOWPLOTS)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(PluginIds.SharedSettings.FILTER)
                .component_unique_id(Filter.Ids.PHASE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(PluginIds.SharedSettings.SHOWPLOTS)
                .component_unique_id(ShowPlots.Ids.SHOWPLOTS)
                .to_string(),
                "value",
            ),
        )
        def _set_available_plots(
            phase: str,
            values: List[str],
        ) -> Tuple[List[dict], List[str]]:
            visibility_options = self.plot_visibility_options(phase)
            return (
                [{"label": l, "value": v} for v, l in visibility_options.items()],
                [value for value in values if value in visibility_options],
            )

        @callback(
            Output(
                self.layout_element(PvtView.Ids.PVT_GRAPHS).get_unique_id().to_string(),
                "children",
            ),
            Input(
                self.settings_group(PluginIds.SharedSettings.FILTER)
                .component_unique_id(Filter.Ids.COLOR_BY)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(PluginIds.SharedSettings.FILTER)
                .component_unique_id(Filter.Ids.ENSEMBLES)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(PluginIds.SharedSettings.FILTER)
                .component_unique_id(Filter.Ids.PHASE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(PluginIds.SharedSettings.FILTER)
                .component_unique_id(Filter.Ids.PVTNUM)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(PluginIds.SharedSettings.SHOWPLOTS)
                .component_unique_id(ShowPlots.Ids.SHOWPLOTS)
                .to_string(),
                "value",
            ),
        )
        def _update_plots(
            color_by: str,
            selected_ensembles: Union[List[str], str],
            phase: str,
            selected_pvtnum: Union[List[str], str],
            plots_visibility: Union[List[str], str],
        ) -> List[Component]:

            if isinstance(selected_ensembles, list) is False:
                ensembles = [selected_ensembles]
            else:
                ensembles = selected_ensembles
            if isinstance(selected_pvtnum, list) is False:
                pvtnum = [selected_pvtnum]
            else:
                pvtnum = selected_pvtnum

            if len(ensembles) == 0 or len(pvtnum) == 0:
                raise PreventUpdate
            pvt_df = filter_data_frame(self.pvt_df, ensembles, pvtnum)

            if color_by == "ENSEMBLE":
                colors = self.ensemble_colors
            elif color_by == "PVTNUM":
                colors = self.pvtnum_colors

            max_num_columns = 2
            view_elements = []

            current_row_elements = []
            current_column = 0

            current_column = 0
            figure_index = 0

            graph_height = max(45.0, 90.0 / len(plots_visibility))

            for plot in plots_visibility:
                current_element = wcc.WebvizViewElement(
                    id=self.unique_id(plot),
                    children=create_graph(
                        pvt_df,
                        color_by,
                        colors,
                        phase,
                        plot,
                        self.plot_visibility_options(self.phases[phase])[plot],
                        self.plotly_theme,
                        graph_height,
                    ),
                )
                current_row_elements.append(current_element)

                current_column += 1

                if (
                    current_column >= max_num_columns
                    or figure_index == len(plots_visibility) - 1
                ):
                    view_elements.append(
                        wcc.WebvizPluginLayoutRow(current_row_elements)
                    )
                    current_row_elements = []
                    current_column = 0

                figure_index += 1

            return view_elements
