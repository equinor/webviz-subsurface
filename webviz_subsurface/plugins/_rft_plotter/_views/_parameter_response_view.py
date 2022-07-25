from typing import Any, Dict, List, Optional, Union

import webviz_core_components as wcc
from dash import Input, Output, State, callback
from dash.exceptions import PreventUpdate
from webviz_config.webviz_plugin_subclasses import ViewABC

from ...._figures import BarChart, ScatterPlot
from .._business_logic import RftPlotterDataModel, correlate
from .._figures._formation_figure import FormationFigure
from .._shared_settings import ParameterResponseSettings


class ParameterResponseView(ViewABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        PARAMRESP_SETTINGS = "paramresp-settings"
        PARAMRESP_FORMATIONS = "paramresp-formations"
        PARAMRESP_CORR_BARCHART = "paramresp-corr-barchart"
        PARAMRESP_CORR_BARCHART_FIGURE = "paramresp-corr-barchart-figure"
        PARAMRESP_SCATTERPLOT = "paramresp-scatterplot"

    def __init__(self, datamodel: RftPlotterDataModel) -> None:
        super().__init__("RTF parameter response")
        self.datamodel = datamodel
        self.parameter_df = datamodel.param_model.dataframe

        self.add_settings_group(
            ParameterResponseSettings(self.datamodel), self.Ids.PARAMRESP_SETTINGS
        )

        first_column = self.add_column()
        first_column.make_row(ParameterResponseView.Ids.PARAMRESP_CORR_BARCHART)
        first_column.make_row(ParameterResponseView.Ids.PARAMRESP_SCATTERPLOT)

        self.add_column(self.Ids.PARAMRESP_FORMATIONS)


    def get_settings_element_id(self, element_id: str) -> str:
        return (
            self.settings_group(self.Ids.PARAMRESP_SETTINGS)
            .component_unique_id(element_id)
            .to_string()
        )

    def set_callbacks(self) -> None:
        @callback(
            Output(self.get_settings_element_id(
                    ParameterResponseSettings.Ids.PARAMRESP_PARAM), "value"),
            Input(self.Ids.PARAMRESP_CORR_BARCHART_FIGURE, "clickData"),
            State(self.get_settings_element_id(
                    ParameterResponseSettings.Ids.PARAMRESP_CORRTYPE), "value"),
            prevent_initial_call=True,
        )
        def _update_param_from_clickdata(
            corr_vector_clickdata: Union[None, dict],
            corrtype: str,
        ) -> str:
            """Update the selected parameter from clickdata"""
            if corr_vector_clickdata is None or corrtype == "param_vs_sim":
                raise PreventUpdate
            return corr_vector_clickdata.get("points", [{}])[0].get("y")

        @callback(
            Output(self.get_settings_element_id(
                    ParameterResponseSettings.Ids.PARAMRESP_WELL), "value"),
            Input(self.Ids.PARAMRESP_CORR_BARCHART_FIGURE, "clickData"),
            State(self.get_settings_element_id(
                    ParameterResponseSettings.Ids.PARAMRESP_WELL), "value"),
            State(self.get_settings_element_id(
                    ParameterResponseSettings.Ids.PARAMRESP_CORRTYPE), "value"),
            State(self.get_settings_element_id(
                    ParameterResponseSettings.Ids.PARAMRESP_DATE), "value"),
            State(self.get_settings_element_id(
                    ParameterResponseSettings.Ids.PARAMRESP_ZONE), "value"),
            prevent_initial_call=True,
        )
        def _update_selections_from_clickdata(
            corr_vector_clickdata: Union[None, dict],
            well: str,
            corrtype: str,
            date: str,
            zone: str,
        ) -> str:
            """Update well, date and zone from clickdata"""
            if corr_vector_clickdata is None or corrtype == "sim_vs_param":
                raise PreventUpdate

            clickdata = corr_vector_clickdata.get("points", [{}])[0].get("y")
            ls_clickdata = clickdata.split()
            print("click dat ais: ",ls_clickdata)
            dates_in_well, zones_in_well = self.datamodel.well_dates_and_zones(well)
            return  ls_clickdata[0]
                        
        
        @callback(
            Output(
                self.layout_element(self.Ids.PARAMRESP_CORR_BARCHART)
                .get_unique_id()
                .to_string(),
                "children",
            ),
            Output(
                self.layout_element(self.Ids.PARAMRESP_SCATTERPLOT)
                .get_unique_id()
                .to_string(),
                "children",
            ),
            Output(
                self.layout_element(self.Ids.PARAMRESP_FORMATIONS)
                .get_unique_id()
                .to_string(),
                "children",
            ),
            Input(
                self.get_settings_element_id(
                    ParameterResponseSettings.Ids.PARAMRESP_ENSEMBLE
                ),
                "value",
            ),
            Input(
                self.get_settings_element_id(
                    ParameterResponseSettings.Ids.PARAMRESP_WELL
                ),
                "value",
            ),
            Input(
                self.get_settings_element_id(
                    ParameterResponseSettings.Ids.PARAMRESP_DATE
                ),
                "value",
            ),
            Input(
                self.get_settings_element_id(
                    ParameterResponseSettings.Ids.PARAMRESP_ZONE
                ),
                "value",
            ),
            Input(
                self.get_settings_element_id(
                    ParameterResponseSettings.Ids.PARAMRESP_PARAM
                ),
                "value",
            ),
            Input(
                self.get_settings_element_id(
                    ParameterResponseSettings.Ids.PARAMRESP_CORRTYPE
                ),
                "value",
            ),
            Input(
                 {
                    "id": ParameterResponseSettings.Ids.PARAM_FILTER, 
                    "type": "data-store"
                }, 
                "data",
            ),
            Input(
                self.get_settings_element_id(
                    ParameterResponseSettings.Ids.PARAMRESP_DEPTHOPTION
                ),
                "value",
            ),
        )
        # pylint: disable=too-many-locals
        def _update_paramresp_graphs(
            ensemble: str,
            well: str,
            date: str,
            zone: str,
            param: Optional[str],
            corrtype: str,
            real_filter: Dict[str, List[int]],
            depth_option: str,
        ) -> List[Optional[Any]]:
            """Main callback to update the graphs:

            * ranked correlations bar chart
            * response vs param scatter plot
            * formations chart RFT pressure vs depth, colored by parameter value
            """
            (
                df,
                obs,
                obs_err,
                ens_params,
                ens_rfts,
            ) = self.datamodel.create_rft_and_param_pivot_table(
                ensemble=ensemble,
                well=well,
                date=date,
                zone=zone,
                reals=real_filter[ensemble],
                keep_all_rfts=(corrtype == "param_vs_sim"),
            )
            current_key = f"{well} {date} {zone}"

            
            if df is None:
                # This happens if the filtering criterias returns no data
                # Could f.ex happen when there are ensembles with different well names
                return ["No data matching the given filter criterias."] * 3
            if param is not None and param not in ens_params:
                # This happens if the selected parameter does not exist in the
                # selected ensemble
                return ["The selected parameter not valid for selected ensemble."] * 3
            if not ens_params:
                # This happens if there are multiple ensembles and one of the ensembles
                # doesn't have non-constant parameters.
                return ["The selected ensemble has no non-constant parameters."] * 3

            if corrtype == "sim_vs_param" or param is None:
                corrseries = correlate(df[ens_params + [current_key]], current_key)
                param = param if param is not None else corrseries.abs().idxmax()
                corr_title = f"{current_key} vs parameters"
                scatter_x, scatter_y, highlight_bar = param, current_key, param

            if corrtype == "param_vs_sim":
                corrseries = correlate(df[ens_rfts + [param]], param)
                corr_title = f"{param} vs simulated RFTs"
                scatter_x, scatter_y, highlight_bar = param, current_key, current_key

            # Correlation bar chart
            corrfig = BarChart(corrseries, n_rows=15, title=corr_title, orientation="h")
            corrfig.color_bars(highlight_bar, "#007079", 0.5)
            corr_graph = wcc.Graph(
                style={"height": "40vh"},
                config={"displayModeBar": False},
                figure=corrfig.figure,
                id = self.Ids.PARAMRESP_CORR_BARCHART_FIGURE
            )

            # Scatter plot
            scatterplot = ScatterPlot(
                df, scatter_y, scatter_x, "#007079", f"{current_key} vs {param}"
            )
            scatterplot.add_vertical_line_with_error(
                obs,
                obs_err,
                df[param].min(),
                df[param].max(),
            )
            scatter_graph = (
                wcc.Graph(
                    style={"height": "40vh"},
                    config={"displayModeBar": False},
                    figure=scatterplot.figure,
                ),
            )

            # Formations plot
            formations_figure = FormationFigure(
                well=well,
                ertdf=self.datamodel.ertdatadf,
                enscolors=self.datamodel.enscolors,
                depth_option=depth_option,
                date=date,
                ensembles=[ensemble],
                reals=real_filter[ensemble],
                simdf=self.datamodel.simdf,
                obsdf=self.datamodel.obsdatadf,
            )

            if formations_figure.use_ertdf:
                return [
                    corr_graph,
                    scatter_graph,
                    f"Realization lines not available for depth option {depth_option}",
                ]

            if self.datamodel.formations is not None:
                formations_figure.add_formation(
                    self.datamodel.formationdf, fill_color=False
                )

            formations_figure.add_simulated_lines("realization")
            formations_figure.add_additional_observations()
            formations_figure.add_ert_observed()

            df_value_norm = self.datamodel.get_param_real_and_value_df(
                ensemble, parameter=param, normalize=True
            )
            formations_figure.color_by_param_value(df_value_norm, param)

            return [
                corr_graph,
                scatter_graph,
                wcc.Graph(
                    style={"height": "87vh"},
                    figure=formations_figure.figure,
                ),
            ]

    #     # @callback(
    #     #     Output(
    #     #         self.settings_group(self.Ids.PARAM_FILTER_WRAPPER)
    #     #         .component_unique_id(ParameterResponseSettings.Ids.PARAMRESP_PARAM)
    #     #         .to_string(),
    #     #         "value",
    #     #     ),
    #     #     Input(
    #     #         self.layout_element(
    #     #             self.Ids.PARAMRESP_CORR_BARCHART
    #     #         ).component_unique_id(),
    #     #         "clickData",
    #     #     ),
    #     #     State(self.component_unique_id(self.Ids.PARAMRESP_CORRTYPE), "value"),
    #     #     prevent_initial_call=True,
    #     # )
    #     # def _update_param_from_clickdata(
    #     #     corr_vector_clickdata: Union[None, dict],
    #     #     corrtype: str,
    #     # ) -> str:
    #     #     """Update the selected parameter from clickdata"""
    #     #     if corr_vector_clickdata is None or corrtype == "param_vs_sim":
    #     #         raise PreventUpdate
    #     #     return corr_vector_clickdata.get("points", [{}])[0].get("y")

    #     # @callback(
    #     #     Output(self.component_unique_id(self.Ids.PARAMRESP_WELL), "value"),
    #     #     Output(
    #     #         self.component_unique_id(self.Ids.PARAMRESP_DATE_DROPDOWN), "children"
    #     #     ),
    #     #     Output(
    #     #         self.component_unique_id(self.Ids.PARAMRESP_ZONE_DROPDOWN), "children"
    #     #     ),
    #     #     Input(
    #     #         self.component_unique_id(self.Ids.PARAMRESP_CORR_BARCHART_FIGURE),
    #     #         "clickData",
    #     #     ),
    #     #     State(self.component_unique_id(self.Ids.PARAMRESP_CORRTYPE), "value"),
    #     #     State(self.component_unique_id(self.Ids.PARAMRESP_WELL), "value"),
    #     #     State(self.component_unique_id(self.Ids.PARAMRESP_DATE), "value"),
    #     #     State(self.component_unique_id(self.Ids.PARAMRESP_ZONE), "value"),
    #     #     prevent_initial_call=True,
    #     # )
    #     # def _update_selections_from_clickdata(
    #     #     corr_vector_clickdata: Union[None, dict],
    #     #     corrtype: str,
    #     #     well: str,
    #     #     date: str,
    #     #     zone: str,
    #     # ) -> Tuple[str, wcc.Dropdown, wcc.Dropdown]:
    #     #     """Update well, date and zone from clickdata"""
    #     #     if corr_vector_clickdata is None or corrtype == "sim_vs_param":
    #     #         raise PreventUpdate

    #     #     clickdata = corr_vector_clickdata.get("points", [{}])[0].get("y")
    #     #     ls_clickdata = clickdata.split()

    #     #     dates_in_well, zones_in_well = datamodel.well_dates_and_zones(well)
    #     #     dates_dropdown = wcc.Dropdown(
    #     #         label="Date",
    #     #         id=self.component_unique_id(self.Ids.PARAMRESP_DATE),
    #     #         options=[{"label": date, "value": date} for date in dates_in_well],
    #     #         value=ls_clickdata[1],
    #     #         clearable=False,
    #     #     )
    #     #     zones_dropdown = wcc.Dropdown(
    #     #         label="Zone",
    #     #         id=self.component_unique_id(self.Ids.PARAMRESP_ZONE),
    #     #         options=[{"label": zone, "value": zone} for zone in zones_in_well],
    #     #         value=ls_clickdata[2],
    #     #         clearable=False,
    #     #     )

    #     #     return ls_clickdata[0], dates_dropdown, zones_dropdown

    #     # @callback(
    #     #     Output(self.component_unique_id(self.Ids.PARAMRESP_DATE), "options"),
    #     #     Output(self.component_unique_id(self.Ids.PARAMRESP_DATE), "value"),
    #     #     Output(self.component_unique_id(self.Ids.PARAMRESP_ZONE), "options"),
    #     #     Output(self.component_unique_id(self.Ids.PARAMRESP_ZONE), "value"),
    #     #     Input(self.component_unique_id(self.Ids.PARAMRESP_WELL), "value"),
    #     #     State(self.component_unique_id(self.Ids.PARAMRESP_ZONE), "value"),
    #     # )
    #     # def _update_date_and_zone(
    #     #     well: str, zone_state: str
    #     # ) -> Tuple[List[Dict[str, str]], str, List[Dict[str, str]], str]:
    #     #     """Update dates and zones when selecting well. If the current
    #     #     selected zone is also present in the new well it will be kept as value.
    #     #     """
    #     #     dates_in_well, zones_in_well = datamodel.well_dates_and_zones(well)
    #     #     return (
    #     #         [{"label": date, "value": date} for date in dates_in_well],
    #     #         dates_in_well[0],
    #     #         [{"label": zone, "value": zone} for zone in zones_in_well],
    #     #         zone_state if zone_state in zones_in_well else zones_in_well[0],
    #     #     )

    #     # @callback(
    #     #     Output(self.component_unique_id(self.Ids.PARAM_FILTER_WRAPPER), "style"),
    #     #     Input(self.component_unique_id(self.Ids.DISPLAY_PARAM_FILTER), "value"),
    #     # )
    #     # def _show_hide_parameter_filter(display_param_filter: list) -> Dict[str, Any]:
    #     #     """Display/hide parameter filter"""
    #     #     return {"display": "block" if display_param_filter else "none", "flex": 1}
