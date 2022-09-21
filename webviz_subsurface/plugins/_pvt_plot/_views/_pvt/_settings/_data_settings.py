from typing import Dict, List

import pandas as pd
import webviz_core_components as wcc
from dash import Input, Output, callback, html
from dash.development.base_component import Component
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._utils._plot_utils import ColorBy


class DataSettings(SettingsGroupABC):

    PHASES = ["OIL", "GAS", "WATER"]
    phases_additional_info: List[str] = []

    class Ids(StrEnum):
        COLOR_BY = "select-color"
        ENSEMBLES = "ensembles"
        PHASE = "phase"
        PVTNUM = "pvtnum"
        PVTNUM_BOX = "pvtnum-box"
        ENSEMBLES_BOX = "ensembles-box"

    def __init__(self, pvt_data_frame: pd.DataFrame) -> None:
        super().__init__("Data")

        self.pvt_data_frame = pvt_data_frame

        self.ensembles = list(self.pvt_data_frame["ENSEMBLE"].unique())

        self.pvtnum = list(self.pvt_data_frame["PVTNUM"].unique())

        if self.pvt_data_frame["KEYWORD"].str.contains("PVTO").any():
            DataSettings.phases_additional_info.append("PVTO")
        elif self.pvt_data_frame["KEYWORD"].str.contains("PVDO").any():
            DataSettings.phases_additional_info.append("PVDO")
        elif self.pvt_data_frame["KEYWORD"].str.contains("PVCDO").any():
            DataSettings.phases_additional_info.append("PVCDO")
        if self.pvt_data_frame["KEYWORD"].str.contains("PVTG").any():
            DataSettings.phases_additional_info.append("PVTG")
        elif self.pvt_data_frame["KEYWORD"].str.contains("PVDG").any():
            DataSettings.phases_additional_info.append("PVDG")
        if self.pvt_data_frame["KEYWORD"].str.contains("PVTW").any():
            DataSettings.phases_additional_info.append("PVTW")

        self._ensemble_properties: dict = {}
        self._pvtnum_properties: dict = {}

    @property
    def phases(self) -> Dict[str, str]:
        phase_descriptions: Dict[str, str] = {}
        for i, phase in enumerate(DataSettings.PHASES):
            phase_descriptions[phase] = self.phases_additional_info[i]
        return phase_descriptions

    def layout(self) -> List[Component]:
        self._ensemble_properties = dict(
            id=self.register_component_unique_id(DataSettings.Ids.ENSEMBLES),
            label="Ensembles",
            options=[{"label": x, "value": x} for x in self.ensembles],
            vertical=True,
        )
        self._pvtnum_properties = dict(
            id=self.register_component_unique_id(DataSettings.Ids.PVTNUM),
            label="Pvtnum",
            options=[{"label": x, "value": x} for x in self.pvtnum],
            vertical=True,
        )

        return [
            wcc.RadioItems(
                id=self.register_component_unique_id(DataSettings.Ids.COLOR_BY),
                label="Color by",
                options=[{"label": x, "value": x} for x in ColorBy],
                value=ColorBy.ENSEMBLE,
                vertical=True,
            ),
            html.Div(
                id=self.register_component_unique_id(DataSettings.Ids.ENSEMBLES_BOX),
                children=[
                    wcc.Checklist(**self._ensemble_properties, value=self.ensembles)
                ],
            ),
            wcc.Dropdown(
                id=self.register_component_unique_id(DataSettings.Ids.PHASE),
                label="Phase",
                options=[
                    {
                        "label": f"{value.lower().capitalize()} ({info})",
                        "value": value,
                    }
                    for value, info in self.phases.items()
                ],
                value=list(self.phases.items())[0][0],
                clearable=False,
                persistence=False,
            ),
            html.Div(
                id=self.register_component_unique_id(DataSettings.Ids.PVTNUM_BOX),
                children=[
                    wcc.RadioItems(**self._pvtnum_properties, value=self.pvtnum[0])
                ],
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.component_unique_id(DataSettings.Ids.ENSEMBLES_BOX).to_string(),
                "children",
            ),
            Output(
                self.component_unique_id(DataSettings.Ids.PVTNUM_BOX).to_string(),
                "children",
            ),
            Input(
                self.component_unique_id(DataSettings.Ids.COLOR_BY).to_string(), "value"
            ),
        )
        @callback_typecheck
        def _update_ensembles_pvtnum(selected_color_by: ColorBy) -> List[Component]:
            if selected_color_by is ColorBy.ENSEMBLE:
                return [
                    wcc.Checklist(
                        **self._ensemble_properties,
                        value=self.ensembles,
                    ),
                    wcc.RadioItems(
                        **self._pvtnum_properties,
                        value=self.pvtnum[0],
                    ),
                ]
            return [
                wcc.RadioItems(
                    **self._ensemble_properties,
                    value=self.ensembles[0],
                ),
                wcc.Checklist(
                    **self._pvtnum_properties,
                    value=self.pvtnum,
                ),
            ]
