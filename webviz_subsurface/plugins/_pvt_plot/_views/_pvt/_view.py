from typing import Any, Dict, List, Tuple

import pandas as pd
import webviz_core_components as wcc
from dash import ALL, Input, Output, callback
from dash.development.base_component import Component
from webviz_config import WebvizSettings
from webviz_config.webviz_plugin_subclasses import ViewABC

from ._settings_groups import DataSettings, ViewSettings
from ._business_logic._plot_utils import create_graph, filter_data_frame


class PvtView(ViewABC):

    # pylint: disable=too-few-public-methods
    class Ids:
        PVT_GRAPHS = "formation-volume-factor"
        VISCOSITY = "viscosity"
        DENSITY = "density"
        GAS_OIL_RATIO = "gas-oil-ratio"

        DataSettings = "DataSettings"
        SHOWPLOTS = "show-plots"

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
                PvtView.Ids.DataSettings: DataSettings(self.pvt_df),
                PvtView.Ids.SHOWPLOTS: ViewSettings(),
            }
        )

        self.add_column(PvtView.Ids.PVT_GRAPHS)

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
            [
                Output(
                    {
                        "id": self.settings_group(PvtView.Ids.SHOWPLOTS)
                        .component_unique_id(ViewSettings.Ids.SHOWPLOTS)
                        .to_string(),
                        "plot": plot_value,
                    },
                    "style",
                )
                for plot_value in ViewSettings.plot_visibility_options()
            ],
            Input(
                self.settings_group(PvtView.Ids.DataSettings)
                .component_unique_id(DataSettings.Ids.PHASE)
                .to_string(),
                "value",
            ),
        )
        def _set_available_plots(
            phase: str,
        ) -> Tuple[dict, ...]:
            all_visibility_options = ViewSettings.plot_visibility_options()
            visibility_options = ViewSettings.plot_visibility_options(phase)
            return tuple(
                {"display": "block" if plot in visibility_options else "none"}
                for plot in all_visibility_options
            )

        @callback(
            Output(
                self.layout_element(PvtView.Ids.PVT_GRAPHS).get_unique_id().to_string(),
                "children",
            ),
            Input(
                self.settings_group(PvtView.Ids.DataSettings)
                .component_unique_id(DataSettings.Ids.COLOR_BY)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(PvtView.Ids.DataSettings)
                .component_unique_id(DataSettings.Ids.ENSEMBLES)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(PvtView.Ids.DataSettings)
                .component_unique_id(DataSettings.Ids.PHASE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(PvtView.Ids.DataSettings)
                .component_unique_id(DataSettings.Ids.PVTNUM)
                .to_string(),
                "value",
            ),
            Input(
                {
                    "id": self.settings_group(PvtView.Ids.SHOWPLOTS)
                    .component_unique_id(ViewSettings.Ids.SHOWPLOTS)
                    .to_string(),
                    "plot": ALL,
                },
                "id",
            ),
            Input(
                {
                    "id": self.settings_group(PvtView.Ids.SHOWPLOTS)
                    .component_unique_id(ViewSettings.Ids.SHOWPLOTS)
                    .to_string(),
                    "plot": ALL,
                },
                "value",
            ),
        )
        # pylint: disable=too-many-locals
        def _update_plots(
            color_by: str,
            selected_ensembles: Any,
            phase: str,
            selected_pvtnum: Any,
            plots_visibility_ids: List[dict],
            plots_visibility: List[str],
        ) -> List[Component]:

            if isinstance(selected_ensembles, list) is False:
                ensembles = [selected_ensembles]
            else:
                ensembles = selected_ensembles
            if isinstance(selected_pvtnum, list) is False:
                pvtnum = [selected_pvtnum]
            else:
                pvtnum = selected_pvtnum

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

            visible_plots = {
                plot_id["plot"]: plot_id["plot"] in visibility
                for plot_id, visibility in zip(plots_visibility_ids, plots_visibility)
            }

            graph_height = max(45.0, 90.0 / len(plots_visibility))

            for plot in ViewSettings.plot_visibility_options(phase):
                if not visible_plots[plot]:
                    continue

                current_element = wcc.WebvizViewElement(
                    id=self.unique_id(plot),
                    children=create_graph(
                        pvt_df,
                        color_by,
                        colors,
                        phase,
                        plot,
                        ViewSettings.plot_visibility_options(self.phases[phase])[plot],
                        self.plotly_theme,
                        graph_height,
                    ),
                )
                current_row_elements.append(current_element)

                current_column += 1

                if current_column >= max_num_columns:
                    view_elements.append(
                        wcc.WebvizPluginLayoutRow(current_row_elements)
                    )
                    current_row_elements = []
                    current_column = 0

                figure_index += 1

            if len(current_row_elements) > 0:
                view_elements.append(wcc.WebvizPluginLayoutRow(current_row_elements))

            return view_elements
