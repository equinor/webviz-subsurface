from multiprocessing.sharedctypes import Value
import pandas as pd
from typing import List
from dash.development.base_component import Component
from requests import options
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC
import webviz_core_components as wcc


class Filter(SettingsGroupABC):
    class Ids:
        COLOR_BY = "select-color"
        PHASE = "phase"

    def __init__(self, pvt_df : pd.DataFrame) -> None:
        super().__init__("Filter")

        self.color = ["Ensembel","Pvtnum"]

        #add more choices
        self.phase = ["Water (PVTW)", "Oil (PVTO)"]

    def layout(self) ->List[Component]:
        return [
            wcc.RadioItems(
                id = self.register_component_unique_id(Filter.Ids.COLOR_BY),
                label="Color by",
                options =[
                    {"label":"Ensembel", "value":"ensembel"},
                    {"label":"Pvtnum", "value":"pvtnum"},
                    ],
                value ="ensembel",
                vertical= False
                ),
            wcc.Dropdown(
                id = self.register_component_unique_id(Filter.Ids.PHASE),
                label="Phase",
                options =[
                    {"label":"Water (PVTW)", "value":"waterPVTW"},
                    {"label":"Gas (PVTG)", "value":"gasPVTG"},
                    {"label":"Oil (PVTO)", "value":"oilPVTO"},
                    ],
                value ="waterPVTW",
                clearable=False
            )
        ]