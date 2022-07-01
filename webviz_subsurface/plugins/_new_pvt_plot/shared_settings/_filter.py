from typing import List
from dash.development.base_component import Component
from dash import callback, Input, Output

from multiprocessing.sharedctypes import Value
import pandas as pd
from typing import List
from dash.development.base_component import Component
from requests import options
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC
import webviz_core_components as wcc

from .._plugin_ids import PluginIds


class Filter(SettingsGroupABC):
    class Ids:
        COLOR_BY = "select-color"
        ENSEMBLES = "ensembles"
        PHASE = "phase"
        PVTNUM = "Pvtnum"
        SHOWPLOTS = "Show-plots"

    def __init__(self, pvt_df: pd.DataFrame) -> None:
        super().__init__("Filter")

        self.color = ["Ensembel", "Pvtnum"]

        self.ensembles = ["iter-0", "iter-3"]

        self.phase = ["Oil (PVTO)", "Gas (PVTG)", "Water (PVTW)"]

        self.pvtnum = ["1", "2"]

    def layout(self) -> List[Component]:
        return [
            wcc.RadioItems(
                id=self.register_component_unique_id(Filter.Ids.COLOR_BY),
                label="Color by",
                options=[{"label": x, "value": x} for x in self.color],
                value=self.color[0],
                vertical=False,
            ),
            wcc.Checklist(
                id=self.register_component_unique_id(Filter.Ids.ENSEMBLES),
                label="Ensembles",
                options=[{"label": x, "value": x} for x in self.ensembles],
                value=self.ensembles,
                vertical=False,
            ),
            wcc.Dropdown(
                id=self.register_component_unique_id(Filter.Ids.PHASE),
                label="Phase",
                options=[{"label": x, "value": x} for x in self.phase],
                value=self.phase[0],
                clearable=False,
            ),
            wcc.Checklist(
                id=self.register_component_unique_id(Filter.Ids.PVTNUM),
                label="Pvtnum",
                options=[{"label": x, "value": x} for x in self.pvtnum],
                value=self.pvtnum,
                vertical=False,
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.SELECTED_COLOR),'data'),
            Input(self.component_unique_id(Filter.Ids.COLOR_BY).to_string(),'value')
        )
        def _update_color_by(selected_color: str) -> str:
            return selected_color

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.SELECTED_ENSEMBLES),"data"),
            Input(self.component_unique_id(Filter.Ids.ENSEMBLES).to_string(),"value")
        )
        def _update_ensembles(selected_ensembles: List[str]) -> List[str]:
            return selected_ensembles

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.SELECTED_PHASE),'data'),
            Input(self.component_unique_id(Filter.Ids.PHASE).to_string(),'value')
        )
        def _update_phase(selected_phase: str) -> str:
            return selected_phase


        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.SELECTED_PVTNUM),'data'),
            Input(self.component_unique_id(Filter.Ids.PVTNUM).to_string(),'value')
        )
        def _update_pvtnum(selected_pvtnum: str) -> str:
            return selected_pvtnum