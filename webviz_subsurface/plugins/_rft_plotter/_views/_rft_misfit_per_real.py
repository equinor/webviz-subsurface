from typing import List, Union

import webviz_core_components as wcc
from dash import Input, Output, callback
from webviz_config.webviz_plugin_subclasses import ViewABC

from .._business_logic import RftPlotterDataModel, filter_frame
from .._figures._misfit_figure import update_misfit_plot
from .._shared_settings import FilterLayout


class RftMisfitPerReal (ViewABC):
    class Ids:
        MISFITPLOT_SETTINGS = "misfitplot-settings"
        MISFITPLOT_GRAPH = "misfitplot-graph"

    def __init__(self, datamodel: RftPlotterDataModel, tab: str) -> None:
        super().__init__("RTF misfit per real")
        self.datamodel = datamodel
        self.tab = tab

        self.add_settings_group(
            FilterLayout(self.datamodel, self.tab),
            self.Ids.MISFITPLOT_SETTINGS
        )

        column = self.add_column()
        column.make_row(self.Ids.MISFITPLOT_GRAPH)
    
    def get_settings_element_id(self,element_id: str) -> str:
        return (
            self.settings_group(self.Ids.MISFITPLOT_SETTINGS)
            .component_unique_id(element_id)
            .to_string()
        )

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.layout_element(self.Ids.MISFITPLOT_GRAPH)
                .get_unique_id()
                .to_string()
                , "children"),
            Input(self.get_settings_element_id(FilterLayout.Ids.FILTER_WELLS[self.tab]), "value"),
            Input(self.get_settings_element_id(FilterLayout.Ids.FILTER_ZONES[self.tab]), "value"),
            Input(self.get_settings_element_id(FilterLayout.Ids.FILTER_DATES[self.tab]), "value"),
            Input(self.get_settings_element_id(FilterLayout.Ids.FILTER_ENSEMBLES[self.tab]), "value"),
        )
        def _misfit_plot(
            wells: List[str], zones: List[str], dates: List[str], ensembles: List[str]
        ) -> Union[str, List[wcc.Graph]]:
            df = filter_frame(
                self.datamodel.ertdatadf,
                {"WELL": wells, "ZONE": zones, "DATE": dates, "ENSEMBLE": ensembles},
            )
            if df.empty:
                return "No data matching the given filter criterias"

            return update_misfit_plot(df, self.datamodel.enscolors)
    