from turtle import settiltangle
from typing import List

import webviz_core_components as wcc
from dash import Input, Output, callback, dcc, html
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._plugin_ids import PlugInIDs


class WaterSettings(SettingsGroupABC):
    class IDs:
        # pylint: disable=too-few-public-methods
        SELECT_QC = "select-qc"
        EQLNUM = "eqlnum"
        COLOR_BY = "color-by"
        MAX_POINTS = "max-points"
        QC_FLAG = "qc-flag"
        SATNUM = "satnum"

    def __init__(self) -> None:
        super().__init__()


class Selections(SettingsGroupABC):
    class IDs:
        # pylint: disable=too-few-public-methods
        SELECT_QC = "select-qc"
        EQLNUM = "eqlnum"
        COLOR_BY = "color-by"
        MAX_POINTS = "max-points"

    def __init__(self, datamodel) -> None:
        super().__init__("Selections")
        self.datamodel = datamodel

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Select QC-visualization:",
                id=self.register_component_unique_id(Selections.IDs.SELECT_QC),
                options=[
                    {
                        "label": "Waterfall plot for water vol changes",
                        "value": self.MainPlots.WATERFALL,
                    },
                    {
                        "label": "Reservoir properties vs Depth",
                        "value": self.MainPlots.PROP_VS_DEPTH,
                    },
                ],
                value=self.MainPlots.PROP_VS_DEPTH,
                clearable=False,
            ),
            wcc.SelectWithLabel(
                label="EQLNUM",
                id=self.register_component_unique_id(Selections.IDs.EQLNUM),
                options=[
                    {"label": ens, "value": ens} for ens in self.datamodel.eqlnums
                ],
                value=self.datamodel.eqlnums[:1],
                size=min(8, len(self.datamodel.eqlnums)),
                multi=True,
            ),
            wcc.Dropdown(
                label="Color by",
                id=self.register_component_unique_id(Selections.IDs.COLOR_BY),
                options=[
                    {"label": ens, "value": ens}
                    for ens in self.datamodel.color_by_selectors
                ],
                value="QC_FLAG",
                clearable=False,
            ),
            wcc.Label("Max number of points:"),
            dcc.Input(
                id=self.register_component_unique_id(Selections.IDs.MAX_POINTS),
                type="number",
                value=5000,
            ),
        ]


"""
    def set_callbacks(self) -> None:
        @callback(
            Output(self.get_store_unique_id(PlugInIDs.Stores.Water.QC_VIZ), "data"),
            Input(self.component_unique_id(Selections.IDs.SELECT_QC), "value"),
        )
        def _set_qc_viz(qc_viz: str) -> str:
            return qc_viz

        @callback(
            Output(self.get_store_unique_id(PlugInIDs.Stores.Water.EQLNUM), "data"),
            Input(self.component_unique_id(Selections.IDs.EQLNUM), "value"),
        )
        def _set_eqlnum(eqlnum: int) -> int:
            return eqlnum

        @callback(
            Output(self.get_store_unique_id(PlugInIDs.Stores.Water.COLOR_BY), "data"),
            Input(self.component_unique_id(Selections.IDs.COLOR_BY), "value"),
        )
        def _set_color_by(color: str) -> str:
            return color

        @callback(
            Output(self.get_store_unique_id(PlugInIDs.Stores.Water.MAX_POINTS), "data"),
            Input(self.component_unique_id(Selections.IDs.MAX_POINTS), "value"),
        )
        def _set_max_points(max: str) -> str:
            return max"""


class Filters(SettingsGroupABC):
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
                id=self.register_component_unique_id(Filters.IDs.QC_FLAG),
                options=[
                    {"label": ens, "value": ens} for ens in self.datamodel.qc_flag
                ],
                value=self.datamodel.qc_flag,
                size=min(8, len(self.datamodel.qc_flag)),
            ),
            wcc.SelectWithLabel(
                label="SATNUM",
                id=self.register_component_unique_id(Filters.IDs.SATNUM),
                options=[
                    {"label": ens, "value": ens} for ens in self.datamodel.satnums
                ],
                value=self.datamodel.satnums,
                size=min(8, len(self.datamodel.satnums)),
            ),
            self.range_filters(
                Filters.IDs.RANGE_FILTERS,
                self.datamodel,
            ),
        ]

    @property
    def range_filters(uuid: str, datamodel: SwatinitQcDataModel) -> List:
        dframe = datamodel.dframe
        filters = []
        for col in datamodel.filters_continuous:
            min_val, max_val = dframe[col].min(), dframe[col].max()
            filters.append(
                wcc.RangeSlider(
                    label="Depth range" if col == "Z" else col,
                    id={"id": uuid, "col": col},
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
