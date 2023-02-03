from typing import Dict, List, Optional, Tuple, Union

import plotly.graph_objects as go
from dash import ALL, Input, Output, State, callback, callback_context
from webviz_config.webviz_plugin_subclasses import ViewABC

from ..._plugin_ids import PlugInIDs
from ..._swatint import SwatinitQcDataModel
from ...view_elements import (
    MapFigure,
    PropertiesVsDepthSubplots,
    WaterfallPlot,
    WaterViewelement,
)
from .settings import WaterFilters, WaterSelections


class TabQqPlotLayout(ViewABC):
    class IDs:
        # pylint: disable=too-few-public-methods
        WATER_TAB = "water-tab"
        MAIN_COLUMN = "main-column"

    def __init__(
        self,
        datamodel: SwatinitQcDataModel,
    ) -> None:
        super().__init__("Water Initialization QC plots")
        self.datamodel = datamodel

        # Need to define these quanitities for the inital case
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

        self.add_settings_group(
            WaterSelections(self.datamodel), PlugInIDs.SettingsGroups.WATER_SEELECTORS
        )
        self.add_settings_group(
            WaterFilters(self.datamodel), PlugInIDs.SettingsGroups.WATER_FILTERS
        )

    def set_callbacks(self) -> None:
        # update
        @callback(
            Output(
                self.view_element(TabQqPlotLayout.IDs.WATER_TAB)
                .component_unique_id(WaterViewelement.IDs.MAIN_FIGURE)
                .to_string(),
                "figure",
            ),
            Output(
                self.view_element(TabQqPlotLayout.IDs.WATER_TAB)
                .component_unique_id(WaterViewelement.IDs.MAP_FIGURE)
                .to_string(),
                "figure",
            ),
            Output(
                self.view_element(TabQqPlotLayout.IDs.WATER_TAB)
                .component_unique_id(WaterViewelement.IDs.INFO_BOX_EQLNUMS)
                .to_string(),
                "children",
            ),
            Output(
                self.view_elements(TabQqPlotLayout.IDs.WATER_TAB).component_unique_id(
                    WaterViewelement.IDs.INFO_BOX_SATNUMS
                ),
                "children",
            ),
            Output(
                self.view_elements(TabQqPlotLayout.IDs.WATER_TAB).component_unique_id(
                    WaterViewelement.IDs.INFO_BOX_VOL_DIFF
                ),
                "children",
            ),
            Input(self.get_store_unique_id(PlugInIDs.Stores.Water.QC_VIZ), "data"),
            Input(self.get_store_unique_id(PlugInIDs.Stores.Water.EQLNUM), "data"),
            Input(self.get_store_unique_id(PlugInIDs.Stores.Water.COLOR_BY), "data"),
            Input(self.get_store_unique_id(PlugInIDs.Stores.Water.MAX_POINTS), "data"),
            Input({"id": WaterFilters.range_filters_id, "col": ALL}, "value"),
            Input({"id": WaterFilters.descreate_filter_id, "col": ALL}, "value"),
            State({"id": WaterFilters.range_filters_id, "col": ALL}, "id"),
            State({"id": WaterFilters.descreate_filter_id, "col": ALL}, "id"),
        )
        # pylint: disable=too-many-arguments
        def _update_plot(
            qc_viz: str,
            eqlnums: List[str],
            color_by: str,
            max_points: int,
            continous_filters_val: List[List[str]],
            descreate_filters_val: List[List[str]],
            continous_filters_ids: List[Dict[str, str]],
            descreate_filters_ids: List[Dict[str, str]],
        ) -> list:

            filters = zip_filters(descreate_filters_val, descreate_filters_ids)
            filters.update({"EQLNUM": eqlnums})

            df = self.datamodel.get_dataframe(
                filters=filters,
                range_filters=zip_filters(continous_filters_val, continous_filters_ids),
            )
            if df.empty:
                return ["No data left after filtering"]

            qc_volumes = self.datamodel.compute_qc_volumes(df)

            df = self.datamodel.filter_dframe_on_depth(df)
            df = self.datamodel.resample_dataframe(df, max_points=max_points)

            colormap = self.datamodel.create_colormap(color_by)
            main_plot = (
                WaterfallPlot(qc_vols=qc_volumes).figure
                if qc_viz == WaterSelections.Values.WATERFALL
                else PropertiesVsDepthSubplots(
                    dframe=df,
                    color_by=color_by,
                    colormap=colormap,
                    discrete_color=color_by in self.datamodel.SELECTORS,
                ).figure
            )
            map_figure = MapFigure(
                dframe=df,
                color_by=color_by,
                faultlinedf=self.datamodel.faultlines_df,
                colormap=colormap,
            ).figure

            return qc_plot_layout.main_layout(
                main_figure=main_plot,
                map_figure=map_figure,
                qc_volumes=qc_volumes,
            )  # this must return something else

        @callback(
            Output(
                self.view_element(TabQqPlotLayout.IDs.WATER_TAB)
                .component_unique_id(WaterViewelement.IDs.MAIN_FIGURE)
                .to_string(),
                "figure",
            ),
            Output(
                self.view_element(TabQqPlotLayout.IDs.WATER_TAB)
                .component_unique_id(WaterViewelement.IDs.MAP_FIGURE)
                .to_string(),
                "figure",
            ),
            Input(
                self.view_element(TabQqPlotLayout.IDs.WATER_TAB)
                .component_unique_id(WaterViewelement.IDs.MAIN_FIGURE)
                .to_string(),
                "selectedData",
            ),
            Input(
                self.view_element(TabQqPlotLayout.IDs.WATER_TAB)
                .component_unique_id(WaterViewelement.IDs.MAP_FIGURE)
                .to_string(),
                "selectedData",
            ),
            State(
                self.view_element(TabQqPlotLayout.IDs.WATER_TAB)
                .component_unique_id(WaterViewelement.IDs.MAIN_FIGURE)
                .to_string(),
                "figure",
            ),
            State(
                self.view_element(TabQqPlotLayout.IDs.WATER_TAB)
                .component_unique_id(WaterViewelement.IDs.MAP_FIGURE)
                .to_string(),
                "figure",
            ),
        )
        def _update_selected_points_in_figure(
            selected_main: dict, selected_map: dict, mainfig: dict, mapfig: dict
        ) -> Tuple[dict, dict]:
            ctx = callback_context.triggered[0]["prop_id"]

            selected = (
                selected_map
                if WaterViewelement.IDs.MAP_FIGURE in ctx
                else selected_main
            )
            point_indexes = get_point_indexes_from_selected(selected)

            for trace in mainfig["data"]:
                update_selected_points_in_trace(trace, point_indexes)
            for trace in mapfig["data"]:
                update_selected_points_in_trace(trace, point_indexes)

            return mainfig, mapfig

        def get_point_indexes_from_selected(
            selected: Optional[dict],
        ) -> Union[list, dict]:
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


def zip_filters(filter_values: list, filter_ids: list) -> dict:
    return {id_val["col"]: values for values, id_val in zip(filter_values, filter_ids)}
