from typing import List, Dict

from dash import callback, Input, Output
import pandas as pd
from webviz_config.webviz_plugin_subclasses import ViewABC
from webviz_config import WebvizSettings

from .._plugin_ids import PluginIds
from ..view_elements import Graph
from ._view_funcions import create_hovertext, create_traces, plot_layout, filter_data_frame, create_graph


class PvtView(ViewABC):
    class Ids:
        # pylint disable too few arguments
        FORMATION_VOLUME_FACTOR = "formation-volume-factor"
        VISCOSITY = "viscosity"
        DENSITY = "density"
        GAS_OIL_RATIO = "gas-oil-ratio"

    def __init__(self, pvt_df: pd.DataFrame, webviz_settings: WebvizSettings) -> None:
        super().__init__("Pvt View")

        self.pvt_df = pvt_df
        self.plotly_theme = webviz_settings.theme.plotly_theme

        column = self.add_column()

        first_row = column.make_row()
        first_row.add_view_element(Graph(), PvtView.Ids.FORMATION_VOLUME_FACTOR)
        first_row.add_view_element(Graph(), PvtView.Ids.VISCOSITY)

        second_row = column.make_row()
        second_row.add_view_element(Graph(), PvtView.Ids.DENSITY)
        second_row.add_view_element(Graph(), PvtView.Ids.GAS_OIL_RATIO)

    @staticmethod
    def plot_visibility_options(phase: str = "") -> Dict[str, str]:
        options = {
            "fvf": "Formation Volume Factor",
            "viscosity": "Viscosity",
            "density": "Density",
        }
        if phase == "PVTO":
            options["ratio"] = "Gas/Oil Ratio (Rs)"
        if phase == "PVTG":
            options["ratio"] = "Vaporized Oil Ratio (Rv)"
        return options
    
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
            Output(self.view_element(PvtView.Ids.FORMATION_VOLUME_FACTOR).component_unique_id(Graph.Ids.GRAPH).to_string(), "figure"),
            Input(self.get_store_unique_id(PluginIds.Stores.SELECTED_COLOR), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.SELECTED_ENSEMBLES), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.SELECTED_PHASE), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.SELECTED_PVTNUM), "data"),
        )
        def _update_plots(
            color_by: str,
            ensembles: List[str],
            phase: str,
            pvtnum: List[str]
        ) -> dict:

            PVT_df = filter_data_frame(self.pvt_df, ensembles, pvtnum)

            if color_by == "ENSEMBLE":
                colors = self.ensemble_colors
            elif color_by == "PVTNUM":
                colors = self.pvtnum_colors

            formation_volume_factor = {
                "data": create_traces(
                            PVT_df,
                            color_by,
                            colors,
                            phase,
                            "RATIO",
                            False,
                            True,
                            True,
                        ),
                "layout": plot_layout(
                            color_by,
                            self.plotly_theme,
                            rf"Pressure [{PVT_df['PRESSURE_UNIT'].iloc[0]}]",
                            rf"[{PVT_df['VOLUMEFACTOR_UNIT'].iloc[0]}]",
                        )
            }
            return formation_volume_factor
