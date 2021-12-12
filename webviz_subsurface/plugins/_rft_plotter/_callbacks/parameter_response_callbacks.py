from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import webviz_core_components as wcc
from dash import Dash, Input, Output, State, callback_context
from dash.exceptions import PreventUpdate

from ...._figures import BarChart, ScatterPlot
from .._business_logic import RftPlotterDataModel, correlate
from .._figures._formation_figure import FormationFigure
from .._layout import LayoutElements


def paramresp_callbacks(
    app: Dash, get_uuid: Callable, datamodel: RftPlotterDataModel
) -> None:
    @app.callback(
        Output(get_uuid(LayoutElements.PARAMRESP_PARAM), "value"),
        Input(get_uuid(LayoutElements.PARAMRESP_CORR_BARCHART), "clickData"),
        State(get_uuid(LayoutElements.PARAMRESP_CORRTYPE), "value"),
        prevent_initial_call=True,
    )
    def _update_parameter_selected(
        corr_vector_clickdata: Union[None, dict],
        corrtype: str,
    ) -> str:
        """Update the selected parameter from clickdata"""
        print("clickdata callback triggered")
        if corr_vector_clickdata is None or corrtype != "sim_vs_param":
            raise PreventUpdate
        return corr_vector_clickdata.get("points", [{}])[0].get("y")

    @app.callback(
        Output(get_uuid(LayoutElements.PARAMRESP_DATE), "options"),
        Output(get_uuid(LayoutElements.PARAMRESP_DATE), "value"),
        Output(get_uuid(LayoutElements.PARAMRESP_ZONE), "options"),
        Output(get_uuid(LayoutElements.PARAMRESP_ZONE), "value"),
        Input(get_uuid(LayoutElements.PARAMRESP_WELL), "value"),
    )
    def _update_date_and_zone(
        well: str,
    ) -> Tuple[List[Dict[str, str]], str, List[Dict[str, str]], str]:
        dates_in_well, zones_in_well = datamodel.well_dates_and_zones(well)
        print("update date and zone triggered")
        return (
            [{"label": date, "value": date} for date in dates_in_well],
            dates_in_well[0],
            [{"label": zone, "value": zone} for zone in zones_in_well],
            zones_in_well[0],
        )

    @app.callback(
        Output(get_uuid(LayoutElements.PARAMRESP_CORR_BARCHART), "figure"),
        Output(get_uuid(LayoutElements.PARAMRESP_SCATTERPLOT), "figure"),
        Output(get_uuid(LayoutElements.PARAMRESP_FORMATIONS), "children"),
        Input(get_uuid(LayoutElements.PARAMRESP_ENSEMBLE), "value"),
        Input(get_uuid(LayoutElements.PARAMRESP_WELL), "value"),
        Input(get_uuid(LayoutElements.PARAMRESP_DATE), "value"),
        Input(get_uuid(LayoutElements.PARAMRESP_ZONE), "value"),
        Input(get_uuid(LayoutElements.PARAMRESP_PARAM), "value"),
        Input(get_uuid(LayoutElements.PARAMRESP_CORRTYPE), "value"),
    )
    # pylint: disable=too-many-locals
    def _update_paramresp_graphs(
        ensemble: str,
        well: str,
        date: str,
        zone: str,
        param: Optional[str],
        corrtype: str,
    ) -> List[Optional[Any]]:
        """
        Main callback to update plots.
        """
        df, obs, obs_err = datamodel.create_rft_and_param_pivot_table(
            ensemble=ensemble,
            well=well,
            date=date,
            zone=zone,
            keep_all_rfts=(corrtype == "param_vs_sim"),
        )
        current_key = f"{well} {date} {zone}"

        if corrtype == "sim_vs_param" or param is None:
            corrseries = correlate(
                df[datamodel.parameters + [current_key]], current_key
            )
            corr_title = f"{current_key} vs parameters"
            corrfig = BarChart(corrseries, n_rows=15, title=corr_title, orientation="h")
            param = param if param is not None else corrfig.first_y_value
            corrfig.color_bars(param, "#007079", 0.5)
            scatter_x, scatter_y = param, current_key

        if corrtype == "param_vs_sim":
            corr_with = [
                col for col in df.columns if col not in datamodel.parameters
            ] + [param]
            corrseries = correlate(df[corr_with], param)
            corr_title = f"{param} vs simulated RFTs"
            corrfig = BarChart(corrseries, n_rows=15, title=corr_title, orientation="h")
            corrfig.color_bars(current_key, "#007079", 0.5)
            scatter_x, scatter_y = param, current_key

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

        # Formations plot
        formations_figure = FormationFigure(
            well=well,
            ertdf=datamodel.ertdatadf,
            enscolors=datamodel.enscolors,
            depth_option="TVD",
            date=date,
            ensembles=[ensemble],
            simdf=datamodel.simdf,
            obsdf=datamodel.obsdatadf,
        )

        if datamodel.formations is not None:
            formations_figure.add_formation(datamodel.formationdf, fill_color=False)

        formations_figure.add_simulated_lines("realization")
        formations_figure.add_additional_observations()
        formations_figure.add_ert_observed()

        df_value_norm = datamodel.get_param_real_and_value_df(
            ensemble, parameter=param, normalize=True
        )
        formations_figure.color_by_param_value(df_value_norm, param)

        return [
            corrfig.figure,
            scatterplot.figure,
            wcc.Graph(
                style={"height": "87vh"},
                figure=formations_figure.figure,
            ),
        ]
