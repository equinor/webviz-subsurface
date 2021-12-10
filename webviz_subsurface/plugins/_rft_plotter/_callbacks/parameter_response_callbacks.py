from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import webviz_core_components as wcc
from dash import Dash, Input, Output, State, callback_context
from dash.exceptions import PreventUpdate

from ...._figures import BarChart, ScatterPlot
from .._business_logic import RftPlotterDataModel, correlate, filter_frame
from .._figures._formation_figure import FormationFigure
from .._layout import LayoutElements


def paramresp_callbacks(
    app: Dash, get_uuid: Callable, datamodel: RftPlotterDataModel
) -> None:
    @app.callback(
        Output(get_uuid(LayoutElements.PARAMRESP_PARAM), "value"),
        Input(get_uuid(LayoutElements.PARAMRESP_CORR_BARCHART), "clickData"),
        State(get_uuid(LayoutElements.PARAMRESP_CORRTYPE), "value"),
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
        print("update paramresp graph triggered")
        if (
            callback_context.triggered is None
            or callback_context.triggered[0]["prop_id"] == "."
        ):
            raise PreventUpdate
        ctx = callback_context.triggered[0]["prop_id"].split(".")[0]
        print(ctx)

        keep = ["REAL", "DATE", "WELL", "ZONE", "SIMULATED", "OBSERVED", "OBSERVED_ERR"]
        rft_df = filter_frame(datamodel.ertdatadf, {"ENSEMBLE": ensemble,}).drop(
            "ENSEMBLE", axis=1
        )[keep]
        rft_df_singleobs = filter_frame(
            rft_df, {"WELL": well, "DATE": date, "ZONE": zone}
        )
        if corrtype == "sim_vs_param":
            rft_df = rft_df_singleobs

        rft_df["RFT_KEY"] = rft_df["WELL"] + "_" + rft_df["DATE"] + "_" + rft_df["ZONE"]
        current_key = f"{well}_{date}_{zone}"
        pivot_df = (
            rft_df.pivot_table(
                index="REAL", columns="RFT_KEY", values="SIMULATED", aggfunc="mean"
            )
            .reset_index()
            .merge(rft_df_singleobs[["REAL", "OBSERVED", "OBSERVED_ERR"]], on="REAL")
        )

        param_df = (
            filter_frame(datamodel.param_model.dataframe, {"ENSEMBLE": ensemble})
            .drop("ENSEMBLE", axis=1)
            .dropna(axis=1)
        )

        merged_df = pivot_df.merge(param_df, on="REAL")

        if corrtype == "sim_vs_param" or param is None:
            corrseries = correlate(
                merged_df[datamodel.parameters + [current_key]], current_key
            )
            corr_title = f"{current_key} vs parameters"
            corrfig = BarChart(corrseries, n_rows=15, title=corr_title, orientation="h")
            param = param if param is not None else corrfig.first_y_value
            corrfig.color_bars(param, "#007079", 0.5)
            scatter_x, scatter_y = param, current_key
        if corrtype == "param_vs_sim":
            corrseries = correlate(merged_df, param)
            corr_title = f"{param} vs simulated RFTs"
            corrfig = BarChart(corrseries, n_rows=15, title=corr_title, orientation="h")
            corrfig.color_bars(current_key, "#007079", 0.5)
            scatter_x, scatter_y = param, current_key

        # Scatter plot
        scatterplot = ScatterPlot(merged_df, scatter_y, scatter_x, "#007079")
        scatterplot.add_vertical_line_with_error(
            merged_df["OBSERVED"].values[0],
            merged_df["OBSERVED_ERR"].values[0],
            merged_df[param].min(),
            merged_df[param].max(),
        )

        # Formations plot
        # trenger bare oppdateres ved ny broenn
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
