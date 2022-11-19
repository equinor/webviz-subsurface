from typing import Any, Dict, List, Union

import webviz_core_components as wcc
from dash import Input, Output, State, callback
from dash.exceptions import PreventUpdate
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import ViewABC

from ..._reusable_view_element import GeneralViewElement
from ..._types import ColorAndSizeByType, DepthType, LineType
from ..._utils import FormationFigure, RftPlotterDataModel
from ._settings import FormationPlotSettings, MapSettings
from ._utils import MapFigure


class MapView(ViewABC):
    class Ids(StrEnum):
        MAP_SETTINGS = "map-settings"
        FORMATION_PLOT_SETTINGS = "formation-plot-settings"
        MAP_VIEW_ELEMENT = "map-view-element"
        FORMATION_PLOT_VIEW_ELEMENT = "formation-plot-view-element"
        MAP_FIGURE = "map-figure"

    def __init__(self, datamodel: RftPlotterDataModel) -> None:
        super().__init__("Map")
        self._datamodel = datamodel

        self.add_settings_group(
            MapSettings(
                ensembles=self._datamodel.ensembles,
                zones=self._datamodel.zone_names,
                date_marks=self._datamodel.date_marks,
                date_range_min=self._datamodel.ertdatadf["DATE_IDX"].min(),
                date_range_max=self._datamodel.ertdatadf["DATE_IDX"].max(),
            ),
            self.Ids.MAP_SETTINGS,
        )
        self.add_settings_group(
            FormationPlotSettings(self._datamodel),
            self.Ids.FORMATION_PLOT_SETTINGS,
        )

        map_column = self.add_column()
        map_column.add_view_element(GeneralViewElement(), self.Ids.MAP_VIEW_ELEMENT)
        formation_plot_column = self.add_column()
        formation_plot_column.add_view_element(
            GeneralViewElement(), self.Ids.FORMATION_PLOT_VIEW_ELEMENT
        )

    def set_callbacks(self) -> None:
        map_figure_id = self.view_element(
            self.Ids.MAP_VIEW_ELEMENT
        ).register_component_unique_id(self.Ids.MAP_FIGURE)

        @callback(
            Output(
                self.settings_group(self.Ids.FORMATION_PLOT_SETTINGS)
                .component_unique_id(FormationPlotSettings.Ids.WELL)
                .to_string(),
                "value",
            ),
            Input(
                map_figure_id,
                "clickData",
            ),
            State(
                self.settings_group(self.Ids.FORMATION_PLOT_SETTINGS)
                .component_unique_id(FormationPlotSettings.Ids.WELL)
                .to_string(),
                "value",
            ),
        )
        def _get_clicked_well(
            click_data: Dict[str, List[Dict[str, Any]]], well: str
        ) -> str:
            if not click_data:
                return well
            for layer in click_data["points"]:
                try:
                    return layer["customdata"]
                except KeyError:
                    pass
            raise PreventUpdate

        @callback(
            Output(
                self.view_element(self.Ids.MAP_VIEW_ELEMENT)
                .component_unique_id(GeneralViewElement.Ids.CHART)
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
                    id=map_figure_id,
                    figure={"data": figure.traces, "layout": figure.layout},
                )
            ]

        @callback(
            Output(
                self.view_element(self.Ids.FORMATION_PLOT_VIEW_ELEMENT)
                .component_unique_id(GeneralViewElement.Ids.CHART)
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
