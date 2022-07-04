from typing import List, Dict
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

    PHASES = ["OIL", "GAS", "WATER"]

    class Ids:
        COLOR_BY = "select-color"
        ENSEMBLES = "ensembles"
        PHASE = "phase"
        PVTNUM = "Pvtnum"
        SHOWPLOTS = "Show-plots"
        PVTNUMBOX = "pvtnum-box"
        ENSEMBLESBOX = "ensembles-box"

    def __init__(self, pvt_data_frame: pd.DataFrame) -> None:
        super().__init__("Filter")

        self.pvtnumID = self.register_component_unique_id(Filter.Ids.PVTNUM)

        self.ensemblesID = self.register_component_unique_id(Filter.Ids.ENSEMBLES)

        self.pvt_data_frame = pvt_data_frame

        self.color = ["ENSEMBLE", "PVTNUM"]

        self.ensembles = list(self.pvt_data_frame["ENSEMBLE"].unique())

        #self.phase = ["Oil (PVTO)", "Gas (PVTG)", "Water (PVTW)"]

        self.pvtnum = list(self.pvt_data_frame["PVTNUM"].unique())

        self.phases_additional_info: List[str] = []
        if self.pvt_data_frame["KEYWORD"].str.contains("PVTO").any():
            self.phases_additional_info.append("PVTO")
        elif self.pvt_data_frame["KEYWORD"].str.contains("PVDO").any():
            self.phases_additional_info.append("PVDO")
        elif self.pvt_data_frame["KEYWORD"].str.contains("PVCDO").any():
            self.phases_additional_info.append("PVCDO")
        if self.pvt_data_frame["KEYWORD"].str.contains("PVTG").any():
            self.phases_additional_info.append("PVTG")
        elif self.pvt_data_frame["KEYWORD"].str.contains("PVDG").any():
            self.phases_additional_info.append("PVDG")
        if self.pvt_data_frame["KEYWORD"].str.contains("PVTW").any():
            self.phases_additional_info.append("PVTW")

    @property
    def phases(self) -> Dict[str, str]:
        phase_descriptions: Dict[str, str] = {}
        for i, phase in enumerate(Filter.PHASES):
            phase_descriptions[phase] = self.phases_additional_info[i]
        return phase_descriptions

    def layout(self) -> List[Component]:
        return [
            wcc.RadioItems(
                id=self.register_component_unique_id(Filter.Ids.COLOR_BY),
                label="Color by",
                options=[{"label": x, "value": x} for x in self.color],
                value=self.color[0],
                vertical=False,
            ),
            wcc.FlexBox(
                id=self.register_component_unique_id(Filter.Ids.ENSEMBLESBOX),
                children =[
                    wcc.Checklist(  
                    id = self.ensemblesID,
                    label="Ensembles",
                    options=[{"label": x, "value": x} for x in self.ensembles],
                    value=self.ensembles,
                    vertical=False
                )]
            ),
            wcc.Dropdown(
                id=self.register_component_unique_id(Filter.Ids.PHASE),
                label="Phase",
                options=[ {
                            "label": f"{value.lower().capitalize()} ({info})",
                            "value": value,
                        }
                        for value, info in self.phases.items()
                        ],
                value=list(self.phases.items())[0][0],
                clearable=False,
            ),
            wcc.FlexBox(
                id=self.register_component_unique_id(Filter.Ids.PVTNUMBOX),
                children =[
                    wcc.Checklist(  
                    id = self.pvtnumID,
                    label="Pvtnum",
                    options=[{"label": x, "value": x} for x in self.pvtnum],
                    value=self.pvtnum[0],
                    vertical=False,
                )]
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
            Input(self.ensemblesID,"value")
        )
        def _update_ensembles(selected_ensembles: List[str]) -> List[str]:
            if type(selected_ensembles) != list:
                selected_ensembles = [selected_ensembles]
            return selected_ensembles

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.SELECTED_PHASE),'data'),
            Input(self.component_unique_id(Filter.Ids.PHASE).to_string(),'value')
        )
        def _update_phase(selected_phase: str) -> str:
            return selected_phase


        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.SELECTED_PVTNUM),'data'),
            Input(self.pvtnumID,'value')
        )
        def _update_pvtnum(selected_pvtnum: List[str]) -> List[str]:
            if type(selected_pvtnum) != list:
                selected_pvtnum = [selected_pvtnum]
            return selected_pvtnum

        @callback(
            Output(self.component_unique_id(Filter.Ids.ENSEMBLESBOX).to_string(),'children'),
            Output(self.component_unique_id(Filter.Ids.PVTNUMBOX).to_string(),'children'),
            Input(self.get_store_unique_id(PluginIds.Stores.SELECTED_COLOR),'data'),
        )
        def _update_ensembles_pvtnum(selected_color_by: str) -> List[Component]:
            if selected_color_by == "ENSEMBLE":
                return [
                        wcc.Checklist(
                            id=self.ensemblesID,  
                            label="Ensembles",
                            options=[{"label": x, "value": x} for x in self.ensembles],
                            value=self.ensembles,
                            vertical=False
                        ),
                        wcc.RadioItems(
                            id=self.pvtnumID,   
                            label="Pvtnum",
                            options=[{"label": x, "value": x} for x in self.pvtnum],
                            value=self.pvtnum[0],
                            vertical=False,
                        ),
                    ]
            else:
                return [
                        wcc.RadioItems(
                            id=self.ensemblesID,   
                            label="Ensembles",
                            options=[{"label": x, "value": x} for x in self.ensembles],
                            value=self.ensembles[0],
                            vertical=False
                        ),
                        wcc.Checklist(
                            id=self.pvtnumID,   
                            label="Pvtnum",
                            options=[{"label": x, "value": x} for x in self.pvtnum],
                            value=self.pvtnum,
                            vertical=False,
                        ),
                    ]
