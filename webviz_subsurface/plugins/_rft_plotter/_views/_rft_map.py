from typing import List, Union

import webviz_core_components as wcc
from dash import Input, Output, callback
from dash.exceptions import PreventUpdate
from webviz_config.webviz_plugin_subclasses import ViewABC

from .._business_logic import RftPlotterDataModel
from .._figures._formation_figure import FormationFigure
from .._figures._map_figure import MapFigure
from .._shared_settings import FormationPlotSelector, MapPlotSelector


class RftMap(ViewABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        MAP_PLOT_SETTINGS = "map-plot-settings"
        FORMATION_PLOT_SETTINGS = "formation-pliot-settings"
        MAP_GRAPH = "map-graph"
        FORMATION_GRAPH = "formation-graph"

    def __init__(self, datamodel: RftPlotterDataModel) -> None:
        super().__init__("RTF Map")
        self.datamodel = datamodel

        self.add_settings_groups(
            {
                self.Ids.MAP_PLOT_SETTINGS: MapPlotSelector(self.datamodel),
                self.Ids.FORMATION_PLOT_SETTINGS: FormationPlotSelector(self.datamodel),
            }
        )

        row = self.add_row()
        row.make_column(RftMap.Ids.MAP_GRAPH)
        row.make_column(RftMap.Ids.FORMATION_GRAPH)

    def get_settings_element_id(self, setting_id: str, element_id: str) -> str:
        return (
            self.settings_group(setting_id).component_unique_id(element_id).to_string()
        )

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.layout_element(self.Ids.MAP_GRAPH).get_unique_id().to_string(),
                "children",
            ),
            Input(
                self.get_settings_element_id(
                    self.Ids.MAP_PLOT_SETTINGS, MapPlotSelector.Ids.MAP_ENSEMBLE
                ),
                "value",
            ),
            Input(
                self.get_settings_element_id(
                    self.Ids.MAP_PLOT_SETTINGS, MapPlotSelector.Ids.MAP_SIZE_BY
                ),
                "value",
            ),
            Input(
                self.get_settings_element_id(
                    self.Ids.MAP_PLOT_SETTINGS, MapPlotSelector.Ids.MAP_COLOR_BY
                ),
                "value",
            ),
            Input(
                self.get_settings_element_id(
                    self.Ids.MAP_PLOT_SETTINGS, MapPlotSelector.Ids.MAP_DATE_RANGE
                ),
                "value",
            ),
            Input(
                self.get_settings_element_id(
                    self.Ids.MAP_PLOT_SETTINGS, MapPlotSelector.Ids.MAP_ZONES
                ),
                "value",
            ),
        )
        def _update_map(
            ensemble: str,
            sizeby: str,
            colorby: str,
            dates: List[float],
            zones: List[str],
        ) -> Union[str, List[wcc.Graph]]:
            figure = MapFigure(self.datamodel.ertdatadf, ensemble, zones)
            if self.datamodel.faultlinesdf is not None:
                figure.add_fault_lines(self.datamodel.faultlinesdf)
            figure.add_misfit_plot(sizeby, colorby, dates)

            return [
                wcc.Graph(
                    style={"height": "84vh"},
                    figure={"data": figure.traces, "layout": figure.layout},
                )
            ]

        @callback(
            Output(
                self.layout_element(self.Ids.FORMATION_GRAPH)
                .get_unique_id()
                .to_string(),
                "children",
            ),
            Input(
                self.get_settings_element_id(
                    self.Ids.FORMATION_PLOT_SETTINGS,
                    FormationPlotSelector.Ids.FORMATIONS_WELL,
                ),
                "value",
            ),
            Input(
                self.get_settings_element_id(
                    self.Ids.FORMATION_PLOT_SETTINGS,
                    FormationPlotSelector.Ids.FORMATIONS_DATE,
                ),
                "value",
            ),
            Input(
                self.get_settings_element_id(
                    self.Ids.FORMATION_PLOT_SETTINGS,
                    FormationPlotSelector.Ids.FORMATIONS_ENSEMBLE,
                ),
                "value",
            ),
            Input(
                self.get_settings_element_id(
                    self.Ids.FORMATION_PLOT_SETTINGS,
                    FormationPlotSelector.Ids.FORMATIONS_LINETYPE,
                ),
                "value",
            ),
            Input(
                self.get_settings_element_id(
                    self.Ids.FORMATION_PLOT_SETTINGS,
                    FormationPlotSelector.Ids.FORMATIONS_DEPTHOPTION,
                ),
                "value",
            ),
        )
        def _update_formation_plot(
            well: str, date: str, ensembles: List[str], linetype: str, depth_option: str
        ) -> Union[str, List[wcc.Graph]]:
            if not ensembles:
                return "No ensembles selected"

            if date not in self.datamodel.date_in_well(well):
                print("prevenr update")
                raise PreventUpdate

            figure = FormationFigure(
                well=well,
                ertdf=self.datamodel.ertdatadf,
                enscolors=self.datamodel.enscolors,
                depth_option=depth_option,
                date=date,
                ensembles=ensembles,
                simdf=self.datamodel.simdf,
                obsdf=self.datamodel.obsdatadf,
            )
            if figure.ertdf.empty:
                return ["No data matching the given filter criterias."]

            if self.datamodel.formations is not None:
                figure.add_formation(self.datamodel.formationdf)

            figure.add_simulated_lines(linetype)
            figure.add_additional_observations()
            figure.add_ert_observed()

            return [
                wcc.Graph(
                    style={"height": "84vh"},
                    figure=figure.figure,
                )
            ]
