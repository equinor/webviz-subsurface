from typing import List

import webviz_core_components as wcc
from dash import Input, Output, callback, dcc
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._plugin_ids import PlugInIDs
from .._swatint import SwatinitQcDataModel


class CapilarSelections(SettingsGroupABC):
    class IDs:
        # pylint: disable=too-few-public-methods
        SPLIT_TABLE_BY = "split-table-by"
        MAX_THRESH = "max-thresh"

    def __init__(self, datamodel: SwatinitQcDataModel) -> None:
        super().__init__("Selections")
        self.datamodel = datamodel

    def layout(self) -> List[Component]:
        return [
            wcc.RadioItems(
                label="Split table by:",
                id=self.register_component_unique_id(
                    CapilarSelections.IDs.SPLIT_TABLE_BY
                ),
                options=[
                    {"label": "SATNUM", "value": "SATNUM"},
                    {"label": "SATNUM and EQLNUM", "value": "both"},
                ],
                value="SATNUM",
            ),
            wcc.Label("Maximum PC_SCALING threshold"),
            dcc.Input(
                id=self.register_component_unique_id(CapilarSelections.IDs.MAX_THRESH),
                type="number",
                persistence=True,
                persistence_type="session",
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.Capilary.SPLIT_TABLE_BY),
                "data",
            ),
            Input(
                self.component_unique_id(
                    CapilarSelections.IDs.SPLIT_TABLE_BY
                ).to_string(),
                "value",
            ),
        )
        def _set_split(split: str) -> str:
            return split

        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.Capilary.MAX_PC_SCALE), "data"
            ),
            Input(
                self.component_unique_id(CapilarSelections.IDs.MAX_THRESH).to_string(),
                "value",
            ),
        )
        def _set_max_pc(max_pc: int) -> int:
            return max_pc


class CapilarFilters(SettingsGroupABC):
    class IDs:
        # pylint: disable=too-few-public-methods
        EQLNUM = "eqlnum"
        RANGE_FILTERS = "range_filters"

    def __init__(self, datamodel: SwatinitQcDataModel) -> None:
        super().__init__("Filter")
        self.datamodel = datamodel

    def layout(self) -> List[Component]:
        return [
            wcc.SelectWithLabel(
                label="EQLNUM",
                id=self.register_component_unique_id(CapilarFilters.IDs.EQLNUM),
                options=[
                    {"label": ens, "value": ens} for ens in self.datamodel.eqlnums
                ],
                value=self.datamodel.eqlnums[:1],
                size=min(8, len(self.datamodel.eqlnums)),
                multi=True,
            ),
            self.range_filters(
                CapilarFilters.IDs.RANGE_FILTERS,
            ),
        ]

    @property
    def range_filters(self, uuid: str) -> List:
        dframe = self.datamodel.dframe
        filters = []
        for col in self.datamodel.filters_continuous:
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
