from typing import Dict, List

import pandas as pd
import webviz_core_components as wcc
from dash import Input, Output, callback, html
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class Filter(SettingsGroupABC):

    PHASES = ["OIL", "GAS", "WATER"]
    phases_additional_info: List[str] = []

    # pylint: disable=too-few-public-methods
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

        self.pvtnum_id = self.register_component_unique_id(Filter.Ids.PVTNUM)

        self.ensembles_id = self.register_component_unique_id(Filter.Ids.ENSEMBLES)

        self.pvt_data_frame = pvt_data_frame

        self.color = ["ENSEMBLE", "PVTNUM"]

        self.ensembles = list(self.pvt_data_frame["ENSEMBLE"].unique())

        self.pvtnum = list(self.pvt_data_frame["PVTNUM"].unique())

        if self.pvt_data_frame["KEYWORD"].str.contains("PVTO").any():
            Filter.phases_additional_info.append("PVTO")
        elif self.pvt_data_frame["KEYWORD"].str.contains("PVDO").any():
            Filter.phases_additional_info.append("PVDO")
        elif self.pvt_data_frame["KEYWORD"].str.contains("PVCDO").any():
            Filter.phases_additional_info.append("PVCDO")
        if self.pvt_data_frame["KEYWORD"].str.contains("PVTG").any():
            Filter.phases_additional_info.append("PVTG")
        elif self.pvt_data_frame["KEYWORD"].str.contains("PVDG").any():
            Filter.phases_additional_info.append("PVDG")
        if self.pvt_data_frame["KEYWORD"].str.contains("PVTW").any():
            Filter.phases_additional_info.append("PVTW")

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
                vertical=True,
            ),
            html.Div(
                id=self.register_component_unique_id(Filter.Ids.ENSEMBLESBOX),
                children=[
                    wcc.Checklist(
                        id=self.register_component_unique_id(Filter.Ids.ENSEMBLES),
                        label="Ensembles",
                        options=[{"label": x, "value": x} for x in self.ensembles],
                        value=self.ensembles,
                        vertical=False,
                    )
                ],
            ),
            wcc.Dropdown(
                id=self.register_component_unique_id(Filter.Ids.PHASE),
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
                id=self.register_component_unique_id(Filter.Ids.PVTNUMBOX),
                children=[
                    wcc.Checklist(
                        id=self.register_component_unique_id(Filter.Ids.PVTNUM),
                        label="Pvtnum",
                        options=[{"label": x, "value": x} for x in self.pvtnum],
                        value=self.pvtnum[0],
                        vertical=False,
                    )
                ],
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.component_unique_id(Filter.Ids.ENSEMBLESBOX).to_string(),
                "children",
            ),
            Output(
                self.component_unique_id(Filter.Ids.PVTNUMBOX).to_string(), "children"
            ),
            Input(self.component_unique_id(Filter.Ids.COLOR_BY).to_string(), "value"),
        )
        def _update_ensembles_pvtnum(selected_color_by: str) -> List[Component]:
            output_list = []
            if selected_color_by == "ENSEMBLE":
                output_list = [
                    wcc.Checklist(
                        id=self.register_component_unique_id(Filter.Ids.ENSEMBLES),
                        label="Ensembles",
                        options=[{"label": x, "value": x} for x in self.ensembles],
                        value=self.ensembles,
                        vertical=False,
                    ),
                    wcc.RadioItems(
                        id=self.register_component_unique_id(Filter.Ids.PVTNUM),
                        label="Pvtnum",
                        options=[{"label": x, "value": x} for x in self.pvtnum],
                        value=self.pvtnum[0],
                        vertical=False,
                    ),
                ]
            else:
                output_list = [
                    wcc.RadioItems(
                        id=self.register_component_unique_id(Filter.Ids.ENSEMBLES),
                        label="Ensembles",
                        options=[{"label": x, "value": x} for x in self.ensembles],
                        value=self.ensembles[0],
                        vertical=False,
                    ),
                    wcc.Checklist(
                        id=self.register_component_unique_id(Filter.Ids.PVTNUM),
                        label="Pvtnum",
                        options=[{"label": x, "value": x} for x in self.pvtnum],
                        value=self.pvtnum,
                        vertical=False,
                    ),
                ]

            return output_list
