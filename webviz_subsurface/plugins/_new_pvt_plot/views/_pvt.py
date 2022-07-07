from typing import List, Dict, Union

from dash import callback, Input, Output
from dash.exceptions import PreventUpdate

from dash.development.base_component import Component
import pandas as pd
from webviz_config.webviz_plugin_subclasses import ViewABC
from webviz_config import WebvizSettings
import webviz_core_components as wcc

from .._plugin_ids import PluginIds
from ._view_funcions import (
    filter_data_frame,
    create_graph,
)
from ..shared_settings._filter import Filter


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

        self.phases_additional_info = Filter.phases_additional_info

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
                self.layout_element(PvtView.Ids.PVT_GRAPHS).get_unique_id().to_string(),
                "children",
            ),
            Input(self.get_store_unique_id(PluginIds.Stores.SELECTED_COLOR), "data"),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_ENSEMBLES), "data"
            ),
            Input(self.get_store_unique_id(PluginIds.Stores.SELECTED_PHASE), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.SELECTED_PVTNUM), "data"),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_SHOW_PLOTS), "data"
            ),
        )
        def _update_plots(
            color_by: str,
            ensembles: List[str],
            phase: str,
            pvtnum: List[str],
            plots_visibility: Union[List[str], str],
        ) -> List[Component]:
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
