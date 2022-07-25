from typing import Any, Dict, List, Tuple

import webviz_core_components as wcc
from dash import Input, Output, State, callback
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ...._components.parameter_filter import ParameterFilter
from .._business_logic import RftPlotterDataModel


class ParameterResponseSettings(SettingsGroupABC): 
    # pylint: disable=too-few-public-methods
    class Ids:
        PARAMRESP_ENSEMBLE = "param-response-ensemble"
        PARAMRESP_WELL = "param-response-well"
        PARAMRESP_DATE = "param-response-date"
        PARAMRESP_ZONE = "param-response-zone"
        PARAMRESP_PARAM = "param-response-param"
        PARAMRESP_CORRTYPE = "param-response-corrtype"
        PARAMRESP_DEPTHOPTION = "paramresp-depthoption"       
        DISPLAY_PARAM_FILTER = "display-param-filter"
        PARAM_FILTER = "param-filter-needs-a-unique-id-here" 
        PARAM_FILTER_WRAPPER = "param-filter-wrapper"

    def __init__(self, datamodel: RftPlotterDataModel) -> None:
        super().__init__("Plot settings")
        self.datamodel = datamodel
        self.ensembles = datamodel.ensembles
        self.well_names = datamodel.well_names
        self.params = datamodel.parameters if not datamodel.parameters is None else []
        self.parameter_df = datamodel.param_model.dataframe

        well = self.well_names[0] if self.well_names else ""

        self.dates_in_well, self.zones_in_well = self.datamodel.well_dates_and_zones(well)

        self.parameter_filter = ParameterFilter(
            uuid= self.Ids.PARAM_FILTER,
            dframe=self.parameter_df[self.parameter_df["ENSEMBLE"].isin(datamodel.param_model.mc_ensembles)].copy(),
            reset_on_ensemble_update=True,
        )

        

    def layout(self) -> List[Component]:
        return [
            wcc.Selectors(
                label="Selections",
                children=[
                    wcc.Dropdown(
                        label="Ensemble",
                        id=self.register_component_unique_id(
                            self.Ids.PARAMRESP_ENSEMBLE
                        ),
                        options=[
                            {"label": ens, "value": ens} for ens in self.ensembles
                        ],
                        value=self.ensembles[0],
                        clearable=False,
                    ),
                    wcc.Dropdown(
                        label="Well",
                        id=self.register_component_unique_id(self.Ids.PARAMRESP_WELL),
                        options=[
                            {"label": well, "value": well} for well in self.well_names
                        ],
                        value=self.well_names[0] if self.well_names else "",
                        clearable=False,
                    ),
                    wcc.Dropdown(
                        label="Date",
                        id=self.register_component_unique_id(self.Ids.PARAMRESP_DATE),
                        options = [{"label": date, "value": date} for date in self.dates_in_well],
                        value = self.dates_in_well[0],
                        clearable=False,
                    ),
                    wcc.Dropdown(
                        label="Zone",
                        id=self.register_component_unique_id(self.Ids.PARAMRESP_ZONE), 
                        options = [{"label": zone, "value": zone} for zone in self.zones_in_well],
                        value = self.zones_in_well[0],                      
                        clearable=False,                        
                    ),
                    wcc.Dropdown(
                        label="Parameter",
                        id=self.register_component_unique_id(self.Ids.PARAMRESP_PARAM),
                        options=[
                            {"label": param, "value": param} for param in self.params
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
                        id=self.register_component_unique_id(
                            self.Ids.PARAMRESP_CORRTYPE
                        ),
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
                        id=self.register_component_unique_id(
                            self.Ids.PARAMRESP_DEPTHOPTION
                        ),
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
                label = "Parameter filter",
                id=self.register_component_unique_id(self.Ids.PARAM_FILTER_WRAPPER),
                style={"display": "none"},
                flex=1,
                children=wcc.Frame(
                    
                    style={"height": "87vh"},
                    children=self.parameter_filter.layout,
                ),

            )
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(self.component_unique_id(self.Ids.PARAM_FILTER_WRAPPER).to_string(), "style"),
            Input(self.component_unique_id(self.Ids.DISPLAY_PARAM_FILTER).to_string(), "value"),
        )
        def _show_hide_parameter_filter(display_param_filter: list) -> Dict[str, Any]:
            """Display/hide parameter filter"""
            return {"display": "block" if display_param_filter else "none", "flex": 1}

        @callback(
            Output(
                 {"id": self.Ids.PARAM_FILTER, "type": "ensemble-update"},
                "data",
            ),
            Input(self.component_unique_id(ParameterResponseSettings.Ids.PARAMRESP_ENSEMBLE).to_string(), "value"),
        )
        def _update_parameter_filter_selection(ensemble: str) -> List[str]:
            """Update ensemble in parameter filter"""
            return [ensemble]

        @callback(
            Output(self.component_unique_id(self.Ids.PARAMRESP_DATE).to_string(), "options"),
            Output(self.component_unique_id(self.Ids.PARAMRESP_DATE).to_string(), "value"),
            Output(self.component_unique_id(self.Ids.PARAMRESP_ZONE).to_string(), "options"),
            Output(self.component_unique_id(self.Ids.PARAMRESP_ZONE).to_string(), "value"),
            Input(self.component_unique_id(self.Ids.PARAMRESP_WELL).to_string(), "value"),
            State(self.component_unique_id(self.Ids.PARAMRESP_ZONE).to_string(), "value"),
        )
        def _update_date_and_zone(
            well: str, zone_state: str
        ) -> Tuple[List[Dict[str, str]], str, List[Dict[str, str]], str]:
            """Update dates and zones when selecting well. If the current
            selected zone is also present in the new well it will be kept as value.
            """
           
            dates_in_well, zones_in_well = self.datamodel.well_dates_and_zones(well)
            return (
                [{"label": date, "value": date} for date in dates_in_well],
                dates_in_well[0],
                [{"label": zone, "value": zone} for zone in zones_in_well],
                zone_state if zone_state in zones_in_well else zones_in_well[0],
            )

