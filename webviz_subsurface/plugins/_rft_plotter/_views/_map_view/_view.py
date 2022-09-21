from typing import List, Union

import webviz_core_components as wcc
from dash import Input, Output, callback
from dash.exceptions import PreventUpdate
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import ViewABC

from ..._types import ColorAndSizeByType, DepthType, LineType
from ..._utils import FormationFigure, RftPlotterDataModel
from ._settings import FormationPlotSettings, MapSettings
from ._utils import MapFigure
from ._view_elements import FormationPlotViewElement, MapViewElement


class MapView(ViewABC):
    class Ids(StrEnum):
        MAP_SETTINGS = "map-settings"
        FORMATION_PLOT_SETTINGS = "formation-plot-settings"
        MAP_VIEW_ELEMENT = "map-view-element"
        FORMATION_PLOT_VIEW_ELEMENT = "formation-plot-view-element"

    def __init__(self, datamodel: RftPlotterDataModel) -> None:
        super().__init__("Map")
        self._datamodel = datamodel

        self.add_settings_group(MapSettings(self._datamodel), self.Ids.MAP_SETTINGS)
        self.add_settings_group(
            FormationPlotSettings(self._datamodel), self.Ids.FORMATION_PLOT_SETTINGS
        )

        map_column = self.add_column()
        map_column.add_view_element(MapViewElement(), self.Ids.MAP_VIEW_ELEMENT)
        formation_plot_column = self.add_column()
        formation_plot_column.add_view_element(
            FormationPlotViewElement(), self.Ids.FORMATION_PLOT_VIEW_ELEMENT
        )

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.view_element(self.Ids.MAP_VIEW_ELEMENT)
                .component_unique_id(MapViewElement.Ids.CHART)
                .to_string(),
                "children",
            ),
            Input(
                self.settings_group(self.Ids.MAP_SETTINGS)
                .component_unique_id(MapSettings.Ids.ENSEMBLE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.MAP_SETTINGS)
                .component_unique_id(MapSettings.Ids.SIZE_BY)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.MAP_SETTINGS)
                .component_unique_id(MapSettings.Ids.COLOR_BY)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.MAP_SETTINGS)
                .component_unique_id(MapSettings.Ids.DATE_RANGE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.MAP_SETTINGS)
                .component_unique_id(MapSettings.Ids.ZONES)
                .to_string(),
                "value",
            ),
        )
        @callback_typecheck
        def _update_map(
            ensemble: str,
            sizeby: ColorAndSizeByType,
            colorby: ColorAndSizeByType,
            dates: List[float],
            zones: List[str],
        ) -> Union[str, List[wcc.Graph]]:
            figure = MapFigure(self._datamodel.ertdatadf, ensemble, zones)
            if self._datamodel.faultlinesdf is not None:
                figure.add_fault_lines(self._datamodel.faultlinesdf)
            figure.add_misfit_plot(sizeby, colorby, dates)

            return [
                wcc.Graph(
                    style={"height": "84vh"},
                    figure={"data": figure.traces, "layout": figure.layout},
                )
            ]

        @callback(
            Output(
                self.view_element(self.Ids.FORMATION_PLOT_VIEW_ELEMENT)
                .component_unique_id(FormationPlotViewElement.Ids.CHART)
                .to_string(),
                "children",
            ),
            Input(
                self.settings_group(self.Ids.FORMATION_PLOT_SETTINGS)
                .component_unique_id(FormationPlotSettings.Ids.WELL)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.FORMATION_PLOT_SETTINGS)
                .component_unique_id(FormationPlotSettings.Ids.DATE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.FORMATION_PLOT_SETTINGS)
                .component_unique_id(FormationPlotSettings.Ids.ENSEMBLE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.FORMATION_PLOT_SETTINGS)
                .component_unique_id(FormationPlotSettings.Ids.LINETYPE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.FORMATION_PLOT_SETTINGS)
                .component_unique_id(FormationPlotSettings.Ids.DEPTH_OPTION)
                .to_string(),
                "value",
            ),
        )
        @callback_typecheck
        def _update_formation_plot(
            well: str,
            date: str,
            ensembles: List[str],
            linetype: LineType,
            depthtype: DepthType,
        ) -> Union[str, List[wcc.Graph]]:
            if not ensembles:
                return "No ensembles selected"

            if date not in self._datamodel.date_in_well(well):
                print("prevenr update")
                raise PreventUpdate

            figure = FormationFigure(
                well=well,
                ertdf=self._datamodel.ertdatadf,
                enscolors=self._datamodel.enscolors,
                depthtype=depthtype,
                date=date,
                ensembles=ensembles,
                simdf=self._datamodel.simdf,
                obsdf=self._datamodel.obsdatadf,
            )
            if figure.ertdf_empty:
                return ["No data matching the given filter criterias."]

            if self._datamodel.formations is not None:
                figure.add_formation(self._datamodel.formationdf)

            figure.add_simulated_lines(linetype)
            figure.add_additional_observations()
            figure.add_ert_observed()

            return [
                wcc.Graph(
                    style={"height": "84vh"},
                    figure=figure.figure,
                )
            ]
