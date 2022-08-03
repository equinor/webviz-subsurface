from typing import List

import webviz_core_components as wcc
from dash import Input, Output, callback, dcc
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._plugin_ids import PlugInIDs
from .._swatint import SwatinitQcDataModel


class WaterSelections(SettingsGroupABC):
    class IDs:
        # pylint: disable=too-few-public-methods
        WATERFALL = "waterfall"
        PROP_VS_DEPTH = "prop-vs-depth"
        SELECT_QC = "select-qc"
        EQLNUM = "eqlnum"
        COLOR_BY = "color-by"
        MAX_POINTS = "max-points"

    def __init__(self, datamodel: SwatinitQcDataModel) -> None:
        super().__init__("Selections")
        self.datamodel = datamodel

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Select QC-visualization:",
                id=self.register_component_unique_id(WaterSelections.IDs.SELECT_QC),
                options=[
                    {
                        "label": "Waterfall plot for water vol changes",
                        "value": WaterSelections.IDs.WATERFALL,
                    },
                    {
                        "label": "Reservoir properties vs Depth",
                        "value": WaterSelections.IDs.PROP_VS_DEPTH,
                    },
                ],
                value=WaterSelections.IDs.PROP_VS_DEPTH,
                clearable=False,
            ),
            wcc.SelectWithLabel(
                label="EQLNUM",
                id=self.register_component_unique_id(WaterSelections.IDs.EQLNUM),
                options=[
                    {"label": ens, "value": ens} for ens in self.datamodel.eqlnums
                ],
                value=self.datamodel.eqlnums[:1],
                size=min(8, len(self.datamodel.eqlnums)),
                multi=True,
            ),
            wcc.Dropdown(
                label="Color by",
                id=self.register_component_unique_id(WaterSelections.IDs.COLOR_BY),
                options=[
                    {"label": ens, "value": ens}
                    for ens in self.datamodel.color_by_selectors
                ],
                value="QC_FLAG",
                clearable=False,
            ),
            wcc.Label("Max number of points:"),
            dcc.Input(
                id=self.register_component_unique_id(WaterSelections.IDs.MAX_POINTS),
                type="number",
                value=5000,
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(self.get_store_unique_id(PlugInIDs.Stores.Water.QC_VIZ), "data"),
            Input(self.component_unique_id(WaterSelections.IDs.SELECT_QC), "value"),
        )
        def _set_qc_viz(qc_viz: str) -> str:
            return qc_viz

        @callback(
            Output(self.get_store_unique_id(PlugInIDs.Stores.Water.EQLNUM), "data"),
            Input(self.component_unique_id(WaterSelections.IDs.EQLNUM), "value"),
        )
        def _set_eqlnum(eqlnum: int) -> int:
            return eqlnum

        @callback(
            Output(self.get_store_unique_id(PlugInIDs.Stores.Water.COLOR_BY), "data"),
            Input(self.component_unique_id(WaterSelections.IDs.COLOR_BY), "value"),
        )
        def _set_color_by(color: str) -> str:
            return color

        @callback(
            Output(self.get_store_unique_id(PlugInIDs.Stores.Water.MAX_POINTS), "data"),
            Input(self.component_unique_id(WaterSelections.IDs.MAX_POINTS), "value"),
        )
        def _set_max_points(max: str) -> str:
            return max


class WaterFilters(SettingsGroupABC):
    class IDs:
        # pylint: disable=too-few-public-methods
        QC_FLAG = "qc-flag"
        SATNUM = "satnum"
        RANGE_FILTERS = "range_filters"

    def __init__(self, datamodel) -> None:
        super().__init__("Filters")
        self.datamodel = datamodel

    def layout(self) -> List[Component]:
        return [
            wcc.SelectWithLabel(
                label="QC_FLAG",
                id=self.register_component_unique_id(WaterFilters.IDs.QC_FLAG),
                options=[
                    {"label": ens, "value": ens} for ens in self.datamodel.qc_flag
                ],
                value=self.datamodel.qc_flag,
                size=min(8, len(self.datamodel.qc_flag)),
            ),
            wcc.SelectWithLabel(
                label="SATNUM",
                id=self.register_component_unique_id(WaterFilters.IDs.SATNUM),
                options=[
                    {"label": ens, "value": ens} for ens in self.datamodel.satnums
                ],
                value=self.datamodel.satnums,
                size=min(8, len(self.datamodel.satnums)),
            ),
            self.range_filters,
        ]

    @property
    def range_filters(self) -> List:
        dframe = self.datamodel.dframe
        filters = []
        for col in self.datamodel.filters_continuous:
            min_val, max_val = dframe[col].min(), dframe[col].max()
            filters.append(
                wcc.RangeSlider(
                    label="Depth range" if col == "Z" else col,
                    id={"id": WaterFilters.IDs.RANGE_FILTERS, "col": col},
                    min=min_val,
                    max=max_val,
                    value=[min_val, max_val],
                    marks={
                        str(val): {"label": f"{val:.2f}"} for val in [min_val, max_val]
                    },
                    tooltip={"always_visible": False},
                )
            )
        return filters

    def set_callbacks(self) -> None:
        @callback(
            Output(self.get_store_unique_id(PlugInIDs.Stores.Water.QC_FLAG), "data"),
            Input(
                self.component_unique_id(WaterFilters.IDs.QC_FLAG).to_string(), "value"
            ),
        )
        def _set_qc_flag(qc_flag: List[str]) -> List[str]:
            return qc_flag

        @callback(
            Output(self.get_store_unique_id(PlugInIDs.Stores.Water.SATNUM), "data"),
            Input(self.component_unique_id(WaterFilters.IDs.SATNUM), "value"),
        )
        def _set_satnum(satnum: List[int]) -> List[int]:
            return satnum
