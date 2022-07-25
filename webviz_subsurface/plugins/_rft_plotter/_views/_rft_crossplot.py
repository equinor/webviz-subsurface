from typing import List, Union

import webviz_core_components as wcc
from dash import Input, Output, callback
from webviz_config.webviz_plugin_subclasses import ViewABC

from .._business_logic import RftPlotterDataModel, filter_frame
from .._figures._crossplot_figure import update_crossplot
from .._shared_settings import FilterLayout, SizeColorLayout


class RftCrossplot (ViewABC):
    # pylint: disable=too-few-public-methods 
    class Ids:
        CROSSPLOT_FILTERS = "crossplot-filters"
        CROSSPLOT_PLOT_SETTINGS = "crossplot-plot-settings"
        CROSSPLOT_GRAPH = "crossplot-graph"

    def __init__(self, datamodel: RftPlotterDataModel, tab: str) -> None:
        super().__init__("RTF crossplot - sim vs obs")
        self.datamodel = datamodel
        self.tab = tab

        self.add_settings_groups(  
            {
                self.Ids.CROSSPLOT_FILTERS: FilterLayout(self.datamodel, self.tab),
                self.Ids.CROSSPLOT_PLOT_SETTINGS: SizeColorLayout(self.datamodel), 
            }      
        )

        self.add_row(self.Ids.CROSSPLOT_GRAPH)
    
    def get_settings_element_id(self,element_id: str, setting_id: str) -> str:
        return (
            self.settings_group(setting_id)
            .component_unique_id(element_id)
            .to_string()
        )

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.layout_element(self.Ids.CROSSPLOT_GRAPH)
                .get_unique_id()
                .to_string()
                , "children"),
            Input(
                self.get_settings_element_id(
                    FilterLayout.Ids.FILTER_WELLS[self.tab],
                    self.Ids.CROSSPLOT_FILTERS
                )
                , "value"),
            Input(
                self.get_settings_element_id(
                    FilterLayout.Ids.FILTER_ZONES[self.tab],
                    self.Ids.CROSSPLOT_FILTERS
                ), 
                "value"
            ),
            Input(
                self.get_settings_element_id(
                    FilterLayout.Ids.FILTER_DATES[self.tab],
                    self.Ids.CROSSPLOT_FILTERS
                )
                , "value"),
            Input(
                self.get_settings_element_id(
                    FilterLayout.Ids.FILTER_ENSEMBLES[self.tab],
                    self.Ids.CROSSPLOT_FILTERS
                ), 
                "value"
            ),
            Input(
                self.get_settings_element_id(
                    SizeColorLayout.Ids.CROSSPLOT_COLOR_BY,
                    self.Ids.CROSSPLOT_PLOT_SETTINGS
                ), 
                "value"
            ),
            Input(
                self.get_settings_element_id(
                    SizeColorLayout.Ids.CROSSPLOT_COLOR_BY,
                    self.Ids.CROSSPLOT_PLOT_SETTINGS
                ), 
                "value"
            ),
        )
        def _crossplot(
            wells: List[str],
            zones: List[str],
            dates: List[str],
            ensembles: List[str],
            sizeby: str,
            colorby: str,
        ) -> Union[str, List[wcc.Graph]]:
            df = filter_frame(
                self.datamodel.ertdatadf,
                {"WELL": wells, "ZONE": zones, "DATE": dates, "ENSEMBLE": ensembles},
            )
            if df.empty:
                return "No data matching the given filter criterias"

            return update_crossplot(df, sizeby, colorby)
    