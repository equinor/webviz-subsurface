from typing import Dict, List, Tuple

import webviz_core_components as wcc
from dash import Input, Output, State, callback
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._business_logic import RftPlotterDataModel, filter_frame


class FormationPlotSelector(SettingsGroupABC):
    # pylint: disable=too-few-public-methods 
    class Ids:
        FORMATIONS_ENSEMBLE = "formations-ensemble"
        FORMATIONS_WELL = "formations-well"
        FORMATIONS_DATE = "formations-date"
        FORMATIONS_LINETYPE = "formations-linetype"
        FORMATIONS_DEPTHOPTION = "formations-depthoption"

    def __init__(self, datamodel: RftPlotterDataModel) -> None:
        super().__init__("Formation plot settings")
        self.datamodel = datamodel
        self.ensembles = datamodel.ensembles
        self.well_names = datamodel.well_names
        self.date_in_well = datamodel.date_in_well

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Ensemble",
                id=self.register_component_unique_id(self.Ids.FORMATIONS_ENSEMBLE),
                options=[{"label": ens, "value": ens} for ens in self.ensembles],
                value=self.ensembles[0],
                multi=True,
                clearable=False,
            ),
            wcc.Dropdown(
                label="Well",
                id=self.register_component_unique_id(self.Ids.FORMATIONS_WELL),
                options=[{"label": well, "value": well} for well in self.well_names],
                value=self.well_names[0],
                clearable=False,
            ),
            wcc.Dropdown(
                label="Date",
                id=self.register_component_unique_id(self.Ids.FORMATIONS_DATE),
                options=[
                    {"label": date, "value": date}
                    for date in self.date_in_well(self.well_names[0])
                ],
                clearable=False,
                value=self.date_in_well(self.well_names[0])[0],
            ),
            wcc.RadioItems(
                label="Plot simulations as",
                id=self.register_component_unique_id(self.Ids.FORMATIONS_LINETYPE),
                options=[
                    {
                        "label": "Realization lines",
                        "value": "realization",
                    },
                    {
                        "label": "Statistical fanchart",
                        "value": "fanchart",
                    },
                ],
                value="realization",
            ),
            wcc.RadioItems(
                label="Depth option",
                id=self.register_component_unique_id(self.Ids.FORMATIONS_DEPTHOPTION),
                options=[
                    {
                        "label": "TVD",
                        "value": "TVD",
                    },
                    {
                        "label": "MD",
                        "value": "MD",
                    },
                ],
                value="TVD",
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(self.component_unique_id(self.Ids.FORMATIONS_LINETYPE).to_string(), "options"),
            Output(self.component_unique_id(self.Ids.FORMATIONS_LINETYPE).to_string(), "value"),
            Input(self.component_unique_id(self.Ids.FORMATIONS_DEPTHOPTION).to_string(), "value"),
            State(self.component_unique_id(self.Ids.FORMATIONS_LINETYPE).to_string(), "value"),
            State(self.component_unique_id(self.Ids.FORMATIONS_WELL).to_string(), "value"),
            State(self.component_unique_id(self.Ids.FORMATIONS_DATE).to_string(), "value"),
        )
        def _update_linetype(
            depth_option: str,
            current_linetype: str,
            current_well: str,
            current_date: str,
        ) -> Tuple[List[Dict[str, str]], str]:
            if self.datamodel.simdf is not None:
                df = filter_frame(
                    self.datamodel.simdf,
                    {"WELL": current_well, "DATE": current_date},
                )
                if depth_option == "TVD" or (
                    depth_option == "MD"
                    and "CONMD" in self.datamodel.simdf
                    and len(df["CONMD"].unique()) == len(df["DEPTH"].unique())
                ):

                    return [
                        {
                            "label": "Realization lines",
                            "value": "realization",
                        },
                        {
                            "label": "Statistical fanchart",
                            "value": "fanchart",
                        },
                    ], current_linetype

            return [
                {
                    "label": "Realization lines",
                    "value": "realization",
                },
            ], "realization"

        @callback(
            Output(self.component_unique_id(self.Ids.FORMATIONS_DATE).to_string(), "options"),
            Output(self.component_unique_id(self.Ids.FORMATIONS_DATE).to_string(), "value"),
            Input(self.component_unique_id(self.Ids.FORMATIONS_WELL).to_string(), "value"),
            State(self.component_unique_id(self.Ids.FORMATIONS_DATE).to_string(), "value"),
        )
        def _update_date(well: str, current_date: str) -> Tuple[List[Dict[str, str]], str]:
            dates = self.datamodel.date_in_well(well)
            available_dates = [{"label": date, "value": date} for date in dates]
            date = current_date if current_date in dates else dates[0]
            return available_dates, date

