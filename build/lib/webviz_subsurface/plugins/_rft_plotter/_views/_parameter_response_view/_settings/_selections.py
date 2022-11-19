from typing import Dict, List, Tuple

import webviz_core_components as wcc
from dash import Input, Output, State, callback
from dash.development.base_component import Component
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ...._utils import RftPlotterDataModel


class Selections(SettingsGroupABC):
    class Ids(StrEnum):
        ENSEMBLE = "param-response-ensemble"
        WELL = "param-response-well"
        DATE = "param-response-date"
        ZONE = "param-response-zone"
        PARAM = "param-response-param"

    def __init__(self, datamodel: RftPlotterDataModel) -> None:
        super().__init__("Selections")
        self._datamodel = datamodel
        self._ensembles = datamodel.ensembles
        self._well_names = datamodel.well_names
        self._params = datamodel.parameters if not datamodel.parameters is None else []
        self._parameter_df = datamodel.param_model.dataframe

        well = self._well_names[0] if self._well_names else ""

        self._dates_in_well, self._zones_in_well = self._datamodel.well_dates_and_zones(
            well
        )

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Ensemble",
                id=self.register_component_unique_id(self.Ids.ENSEMBLE),
                options=[{"label": ens, "value": ens} for ens in self._ensembles],
                value=self._ensembles[0],
                clearable=False,
            ),
            wcc.Dropdown(
                label="Well",
                id=self.register_component_unique_id(self.Ids.WELL),
                options=[{"label": well, "value": well} for well in self._well_names],
                value=self._well_names[0] if self._well_names else "",
                clearable=False,
            ),
            wcc.Dropdown(
                label="Date",
                id=self.register_component_unique_id(self.Ids.DATE),
                options=[
                    {"label": date, "value": date} for date in self._dates_in_well
                ],
                value=self._dates_in_well[0],
                clearable=False,
            ),
            wcc.Dropdown(
                label="Zone",
                id=self.register_component_unique_id(self.Ids.ZONE),
                options=[
                    {"label": zone, "value": zone} for zone in self._zones_in_well
                ],
                value=self._zones_in_well[0],
                clearable=False,
            ),
            wcc.Dropdown(
                label="Parameter",
                id=self.register_component_unique_id(self.Ids.PARAM),
                options=[{"label": param, "value": param} for param in self._params],
                clearable=False,
                value=None,
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(self.component_unique_id(self.Ids.DATE).to_string(), "options"),
            Output(self.component_unique_id(self.Ids.DATE).to_string(), "value"),
            Output(self.component_unique_id(self.Ids.ZONE).to_string(), "options"),
            Output(self.component_unique_id(self.Ids.ZONE).to_string(), "value"),
            Input(self.component_unique_id(self.Ids.WELL).to_string(), "value"),
            State(self.component_unique_id(self.Ids.ZONE).to_string(), "value"),
        )
        @callback_typecheck
        def _update_date_and_zone(
            well: str, zone_state: str
        ) -> Tuple[List[Dict[str, str]], str, List[Dict[str, str]], str]:
            """Update dates and zones when selecting well. If the current
            selected zone is also present in the new well it will be kept as value.
            """

            dates_in_well, zones_in_well = self._datamodel.well_dates_and_zones(well)
            return (
                [{"label": date, "value": date} for date in dates_in_well],
                dates_in_well[0],
                [{"label": zone, "value": zone} for zone in zones_in_well],
                zone_state if zone_state in zones_in_well else zones_in_well[0],
            )
