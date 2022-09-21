from typing import Any, Dict, List, Tuple

import webviz_core_components as wcc
from dash import Input, Output, State, callback
from dash.development.base_component import Component
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ....._components.parameter_filter import ParameterFilter
from ..._utils import RftPlotterDataModel


class ParameterResponseSettings(SettingsGroupABC):
    class Ids(StrEnum):
        ENSEMBLE = "param-response-ensemble"
        WELL = "param-response-well"
        DATE = "param-response-date"
        ZONE = "param-response-zone"
        PARAM = "param-response-param"
        CORRTYPE = "param-response-corrtype"
        DEPTHOPTION = "paramresp-depthoption"
        DISPLAY_PARAM_FILTER = "display-param-filter"
        PARAM_FILTER = "param-filter-needs-a-unique-id-here"
        PARAM_FILTER_WRAPPER = "param-filter-wrapper"

    def __init__(self, datamodel: RftPlotterDataModel) -> None:
        super().__init__("Plot settings")
        self._datamodel = datamodel
        self._ensembles = datamodel.ensembles
        self._well_names = datamodel.well_names
        self._params = datamodel.parameters if not datamodel.parameters is None else []
        self._parameter_df = datamodel.param_model.dataframe

        well = self._well_names[0] if self._well_names else ""

        self._dates_in_well, self._zones_in_well = self._datamodel.well_dates_and_zones(
            well
        )

        self._parameter_filter = ParameterFilter(
            uuid=self.Ids.PARAM_FILTER,
            dframe=self._parameter_df[
                self._parameter_df["ENSEMBLE"].isin(datamodel.param_model.mc_ensembles)
            ].copy(),
            reset_on_ensemble_update=True,
        )

    def layout(self) -> List[Component]:
        return [
            wcc.Selectors(
                label="Selections",
                children=[
                    wcc.Dropdown(
                        label="Ensemble",
                        id=self.register_component_unique_id(self.Ids.ENSEMBLE),
                        options=[
                            {"label": ens, "value": ens} for ens in self._ensembles
                        ],
                        value=self._ensembles[0],
                        clearable=False,
                    ),
                    wcc.Dropdown(
                        label="Well",
                        id=self.register_component_unique_id(self.Ids.WELL),
                        options=[
                            {"label": well, "value": well} for well in self._well_names
                        ],
                        value=self._well_names[0] if self._well_names else "",
                        clearable=False,
                    ),
                    wcc.Dropdown(
                        label="Date",
                        id=self.register_component_unique_id(self.Ids.DATE),
                        options=[
                            {"label": date, "value": date}
                            for date in self._dates_in_well
                        ],
                        value=self._dates_in_well[0],
                        clearable=False,
                    ),
                    wcc.Dropdown(
                        label="Zone",
                        id=self.register_component_unique_id(self.Ids.ZONE),
                        options=[
                            {"label": zone, "value": zone}
                            for zone in self._zones_in_well
                        ],
                        value=self._zones_in_well[0],
                        clearable=False,
                    ),
                    wcc.Dropdown(
                        label="Parameter",
                        id=self.register_component_unique_id(self.Ids.PARAM),
                        options=[
                            {"label": param, "value": param} for param in self._params
                        ],
                        clearable=False,
                        value=None,
                    ),
                ],
            ),
            wcc.Selectors(
                label="Options",
                children=[
                    wcc.Checklist(
                        id=self.register_component_unique_id(
                            self.Ids.DISPLAY_PARAM_FILTER
                        ),
                        options=[{"label": "Show parameter filter", "value": "Show"}],
                        value=[],
                    ),
                    wcc.RadioItems(
                        label="Correlation options",
                        id=self.register_component_unique_id(self.Ids.CORRTYPE),
                        options=[
                            {
                                "label": "Simulated vs parameters",
                                "value": "sim_vs_param",
                            },
                            {
                                "label": "Parameter vs simulated",
                                "value": "param_vs_sim",
                            },
                        ],
                        value="sim_vs_param",
                    ),
                    wcc.RadioItems(
                        label="Depth option",
                        id=self.register_component_unique_id(self.Ids.DEPTHOPTION),
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
                ],
            ),
            wcc.Selectors(
                label="Parameter filter",
                id=self.register_component_unique_id(self.Ids.PARAM_FILTER_WRAPPER),
                style={"display": "none"},
                flex=1,
                children=wcc.Frame(
                    style={"height": "87vh"},
                    children=self._parameter_filter.layout,
                ),
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.component_unique_id(self.Ids.PARAM_FILTER_WRAPPER).to_string(),
                "style",
            ),
            Input(
                self.component_unique_id(self.Ids.DISPLAY_PARAM_FILTER).to_string(),
                "value",
            ),
        )
        def _show_hide_parameter_filter(display_param_filter: list) -> Dict[str, Any]:
            """Display/hide parameter filter"""
            return {"display": "block" if display_param_filter else "none", "flex": 1}

        @callback(
            Output(
                {"id": self.Ids.PARAM_FILTER, "type": "ensemble-update"},
                "data",
            ),
            Input(
                self.component_unique_id(
                    ParameterResponseSettings.Ids.ENSEMBLE
                ).to_string(),
                "value",
            ),
        )
        def _update_parameter_filter_selection(ensemble: str) -> List[str]:
            """Update ensemble in parameter filter"""
            return [ensemble]

        @callback(
            Output(self.component_unique_id(self.Ids.DATE).to_string(), "options"),
            Output(self.component_unique_id(self.Ids.DATE).to_string(), "value"),
            Output(self.component_unique_id(self.Ids.ZONE).to_string(), "options"),
            Output(self.component_unique_id(self.Ids.ZONE).to_string(), "value"),
            Input(self.component_unique_id(self.Ids.WELL).to_string(), "value"),
            State(self.component_unique_id(self.Ids.ZONE).to_string(), "value"),
        )
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
