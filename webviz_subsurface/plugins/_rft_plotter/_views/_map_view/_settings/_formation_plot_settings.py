from typing import Dict, List, Tuple

import webviz_core_components as wcc
from dash import Input, Output, State, callback
from dash.development.base_component import Component
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ...._utils import RftPlotterDataModel, filter_frame


class FormationPlotSettings(SettingsGroupABC):
    class Ids(StrEnum):
        ENSEMBLE = "ensemble"
        WELL = "well"
        DATE = "date"
        LINETYPE = "linetype"
        DEPTH_OPTION = "depth-option"

    def __init__(self, datamodel: RftPlotterDataModel) -> None:
        super().__init__("Formation plot settings")
        self._datamodel = datamodel
        self._ensembles = datamodel.ensembles
        self._well_names = datamodel.well_names

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Ensemble",
                id=self.register_component_unique_id(self.Ids.ENSEMBLE),
                options=[{"label": ens, "value": ens} for ens in self._ensembles],
                value=self._ensembles[0],
                multi=True,
                clearable=False,
            ),
            wcc.Dropdown(
                label="Well",
                id=self.register_component_unique_id(self.Ids.WELL),
                options=[{"label": well, "value": well} for well in self._well_names],
                value=self._well_names[0],
                clearable=False,
            ),
            wcc.Dropdown(
                label="Date",
                id=self.register_component_unique_id(self.Ids.DATE),
                options=[
                    {"label": date, "value": date}
                    for date in self._datamodel.date_in_well(self._well_names[0])
                ],
                clearable=False,
                value=self._datamodel.date_in_well(self._well_names[0])[0],
            ),
            wcc.RadioItems(
                label="Plot simulations as",
                id=self.register_component_unique_id(self.Ids.LINETYPE),
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
                id=self.register_component_unique_id(self.Ids.DEPTH_OPTION),
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
            Output(
                self.component_unique_id(self.Ids.LINETYPE).to_string(),
                "options",
            ),
            Output(
                self.component_unique_id(self.Ids.LINETYPE).to_string(),
                "value",
            ),
            Input(
                self.component_unique_id(self.Ids.DEPTH_OPTION).to_string(),
                "value",
            ),
            State(
                self.component_unique_id(self.Ids.LINETYPE).to_string(),
                "value",
            ),
            State(self.component_unique_id(self.Ids.WELL).to_string(), "value"),
            State(self.component_unique_id(self.Ids.DATE).to_string(), "value"),
        )
        def _update_linetype(
            depth_option: str,
            current_linetype: str,
            current_well: str,
            current_date: str,
        ) -> Tuple[List[Dict[str, str]], str]:
            if self._datamodel.simdf is not None:
                df = filter_frame(
                    self._datamodel.simdf,
                    {"WELL": current_well, "DATE": current_date},
                )
                if depth_option == "TVD" or (
                    depth_option == "MD"
                    and "CONMD" in self._datamodel.simdf
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
            Output(
                self.component_unique_id(self.Ids.DATE).to_string(),
                "options",
            ),
            Output(self.component_unique_id(self.Ids.DATE).to_string(), "value"),
            Input(self.component_unique_id(self.Ids.WELL).to_string(), "value"),
            State(self.component_unique_id(self.Ids.DATE).to_string(), "value"),
        )
        def _update_date(
            well: str, current_date: str
        ) -> Tuple[List[Dict[str, str]], str]:
            dates = self._datamodel.date_in_well(well)
            available_dates = [{"label": date, "value": date} for date in dates]
            date = current_date if current_date in dates else dates[0]
            return available_dates, date
