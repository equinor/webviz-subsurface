from typing import Optional, Tuple, Union

import plotly.graph_objects as go
from dash import Input, Output, State, callback, callback_context
from webviz_config.webviz_plugin_subclasses import ViewABC

from .._plugin_ids import PlugInIDs
from .._swatint import SwatinitQcDataModel
from ..settings_groups import WaterFilters, WaterSelections
from ..view_elements import WaterViewelement


class TabQqPlotLayout(ViewABC):
    class IDs:
        # pylint: disable=too-few-public-methods
        WATER_TAB = "water-tab"
        MAIN_COLUMN = "main-column"

    def __init__(
        self,
        datamodel: SwatinitQcDataModel,
        main_figure: go.Figure,
        map_figure: go.Figure,
        qc_volumes: dict,
    ) -> None:
        super().__init__("Water Initialization QC plots")
        self.datamodel = datamodel
        self.main_figure = main_figure
        self.map_figure = map_figure
        self.qc_volumes = qc_volumes

        main_column = self.add_column(TabQqPlotLayout.IDs.MAIN_COLUMN)
        row = main_column.make_row()
        row.add_view_element(
            WaterViewelement(
                self.datamodel, self.main_figure, self.map_figure, self.qc_volumes
            ),
            TabQqPlotLayout.IDs.WATER_TAB,
        )

        self.add_settings_group(WaterSelections(self.datamodel), PlugInIDs.SettingsGroups.WATER_SEELECTORS)
        self.add_settings_group(WaterFilters(self.datamodel), PlugInIDs.SettingsGroups.WATER_FILTERS)


    def set_callbacks(self) -> None:
        # update 
        
        
        @callback(
            Output(
                self.view_element(TabQqPlotLayout.IDs.WATER_TAB)
                .component_unique_id(WaterViewelement.IDs.MAIN_FIGURE)
                .to_string(),
                "figure"
            ),
            Output(
                self.view_element(TabQqPlotLayout.IDs.WATER_TAB)
                .component_unique_id(WaterViewelement.IDs.MAP_FIGURE)
                .to_string(),
                "figure"
            ),
            Input(
                self.view_element(TabQqPlotLayout.IDs.WATER_TAB)
                .component_unique_id(WaterViewelement.IDs.MAIN_FIGURE)
                .to_string(),
                "selectedData"
            ),
            Input(
                self.view_element(TabQqPlotLayout.IDs.WATER_TAB)
                .component_unique_id(WaterViewelement.IDs.MAP_FIGURE)
                .to_string(),
                "selectedData"
            ),
            State(
                self.view_element(TabQqPlotLayout.IDs.WATER_TAB)
                .component_unique_id(WaterViewelement.IDs.MAIN_FIGURE)
                .to_string(),
                "figure"
            ),
            State(
                self.view_element(TabQqPlotLayout.IDs.WATER_TAB)
                .component_unique_id(WaterViewelement.IDs.MAP_FIGURE)
                .to_string(),
                "figure"
            ),
        )
        def _update_selected_points_in_figure(selected_main: dict, selected_map: dict, mainfig: dict, mapfig: dict) -> Tuple[dict, dict]:
            ctx = callback_context.triggered[0]["prop_id"]

            selected = (
                selected_map if WaterViewelement.IDs.MAP_FIGURE in ctx else selected_main
            )
            point_indexes = get_point_indexes_from_selected(selected)

            for trace in mainfig["data"]:
                update_selected_points_in_trace(trace, point_indexes)
            for trace in mapfig["data"]:
                update_selected_points_in_trace(trace, point_indexes)

            return mainfig, mapfig


        def get_point_indexes_from_selected(selected: Optional[dict]) -> Union[list, dict]:
            if not (isinstance(selected, dict) and "points" in selected):
                return []

            continous_color = "marker.color" in selected["points"][0]
            if continous_color:
                return [point["pointNumber"] for point in selected["points"]]

            point_indexes: dict = {}
            for point in selected["points"]:
                trace_name = str(point["customdata"][0])
                if trace_name not in point_indexes:
                    point_indexes[trace_name] = []
                point_indexes[trace_name].append(point["pointNumber"])
            return point_indexes


        def update_selected_points_in_trace(
            trace: dict, point_indexes: Union[dict, list]
        ) -> None:
            if "name" in trace:
                selectedpoints = (
                    point_indexes
                    if isinstance(point_indexes, list)
                    else point_indexes.get(trace["name"], [])
                )
                trace.update(selectedpoints=selectedpoints if point_indexes else None)