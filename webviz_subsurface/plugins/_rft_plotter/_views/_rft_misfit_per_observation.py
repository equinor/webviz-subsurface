from typing import List, Union

import webviz_core_components as wcc
from dash import Input, Output, callback
from webviz_config.webviz_plugin_subclasses import ViewABC

from .._business_logic import RftPlotterDataModel, filter_frame
from .._figures._errorplot_figure import update_errorplot
from .._shared_settings import FilterLayout


class RftMisfitPerObservation (ViewABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        ERRORPLOT_SETTINGS = "errorplot-settings"
        ERRORPLOT_GRAPH = "errorplot-graph"

    def __init__(self, datamodel: RftPlotterDataModel, tab: str) -> None:
        super().__init__("RTF misfit per observation")
        self.datamodel = datamodel
        self.tab = tab

        self.add_settings_group(
            FilterLayout(self.datamodel, self.tab),
            self.Ids.ERRORPLOT_SETTINGS
        )

        self.add_column(self.Ids.ERRORPLOT_GRAPH)
    
    def get_settings_element_id(self,element_id: str) -> str:
        return (
            self.settings_group(self.Ids.ERRORPLOT_SETTINGS)
            .component_unique_id(element_id)
            .to_string()
        )

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.layout_element(self.Ids.ERRORPLOT_GRAPH)
                .get_unique_id()
                .to_string()
                , "children"),
            Input(self.get_settings_element_id(FilterLayout.Ids.FILTER_WELLS[self.tab]), "value"),
            Input(self.get_settings_element_id(FilterLayout.Ids.FILTER_ZONES[self.tab]), "value"),
            Input(self.get_settings_element_id(FilterLayout.Ids.FILTER_DATES[self.tab]), "value"),
            Input(self.get_settings_element_id(FilterLayout.Ids.FILTER_ENSEMBLES[self.tab]), "value"),
        )
        def _errorplot(
            wells: List[str], zones: List[str], dates: List[str], ensembles: List[str]
        ) -> Union[str, List[wcc.Graph]]:
            df = filter_frame(
                self.datamodel.ertdatadf,
                {"WELL": wells, "ZONE": zones, "DATE": dates, "ENSEMBLE": ensembles},
            )
            if df.empty:
                return "No data matching the given filter criterias"
            return [update_errorplot(df, self.datamodel.enscolors)]
        