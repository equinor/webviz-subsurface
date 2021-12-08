from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import webviz_core_components as wcc
from dash import Dash, Input, Output, callback_context
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
    )
    def _update_parameter_selected(
        corr_vector_clickdata: Union[None, dict],
    ) -> str:
        """Update the selected parameter from clickdata"""
        print("clickdata callback triggered")
        if corr_vector_clickdata is None:
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
    )
    def _update_paramresp_graphs(
        ensemble: str,
        well: str,
        date: str,
        zone: str,
        param: Optional[str],
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

        rft_df = filter_frame(
            datamodel.ertdatadf,
            {
                "ENSEMBLE": ensemble,
                "WELL": well,
                "DATE": date,
                "ZONE": zone,
            },
        ).drop("ENSEMBLE", axis=1)
        # filter columns also?

        if rft_df.empty:
            text = "No data matching the given filter criterias"
            return [text, text, text]

        param_df = filter_frame(
            datamodel.param_model.dataframe, {"ENSEMBLE": ensemble}
        ).drop("ENSEMBLE", axis=1)

        # todo: time these alternative ways
        rft_df["REAL"] = rft_df["REAL"].astype(int)
        param_df["REAL"] = param_df["REAL"].astype(int)
        param_df.set_index("REAL", inplace=True)
        rft_df.set_index("REAL", inplace=True)
        merged_df = rft_df.join(param_df).reset_index()
        # merged_df = rft_df.merge(param_df, on="REAL")

        corrseries = correlate(
            merged_df[datamodel.parameters + ["SIMULATED"]], "SIMULATED"
        )

        # print(corrseries)
        corrfig = BarChart(
            corrseries, n_rows=15, title="Correlations with parameters", orientation="h"
        )
        # Get clicked parameter correlation bar or largest bar initially
        param = param if param is not None else corrfig.first_y_value
        corrfig.color_bars(param, "#007079", 0.5)

        # Scatter plot
        scatterplot = ScatterPlot(merged_df, "SIMULATED", param, "#007079")
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
            formations_figure.add_formation(datamodel.formationdf)

        formations_figure.add_simulated_lines("realization")
        formations_figure.add_additional_observations()
        formations_figure.add_ert_observed()

        return [
            corrfig.figure,
            scatterplot.figure,
            wcc.Graph(
                style={"height": "87vh"},
                figure=formations_figure.figure,
            ),
        ]
