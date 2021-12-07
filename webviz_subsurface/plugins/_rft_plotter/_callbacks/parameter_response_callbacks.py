from typing import Any, Callable, Dict, List, Optional, Tuple

import webviz_core_components as wcc
from dash import Dash, Input, Output

from ...._figures import BarChart, ScatterPlot
from .._business_logic import RftPlotterDataModel, correlate, filter_frame
from .._layout import LayoutElements


def paramresp_callbacks(
    app: Dash, get_uuid: Callable, datamodel: RftPlotterDataModel
) -> None:
    @app.callback(
        Output(get_uuid(LayoutElements.PARAMRESP_DATE), "options"),
        Output(get_uuid(LayoutElements.PARAMRESP_DATE), "value"),
        Output(get_uuid(LayoutElements.PARAMRESP_ZONE), "options"),
        Output(get_uuid(LayoutElements.PARAMRESP_ZONE), "value"),
        Input(get_uuid(LayoutElements.PARAMRESP_WELL), "value"),
    )
    def _update_date(
        well: str,
    ) -> Tuple[List[Dict[str, str]], str, List[Dict[str, str]], str]:
        dates_in_well, zones_in_well = datamodel.well_dates_and_zones(well)
        return (
            [{"label": date, "value": date} for date in dates_in_well],
            dates_in_well[0],
            [{"label": zone, "value": zone} for zone in zones_in_well],
            zones_in_well[0],
        )

    @app.callback(
        Output(get_uuid(LayoutElements.PARAMRESP_RFT_VS_DEPTH_GRAPH), "children"),
        Output(get_uuid(LayoutElements.PARAMRESP_RFT_VS_PARAM_GRAPH), "children"),
        Output(get_uuid(LayoutElements.PARAMRESP_RFT_CORR_GRAPH), "children"),
        Output(get_uuid(LayoutElements.PARAMRESP_PARAM_CORR_GRAPH), "children"),
        Output(get_uuid(LayoutElements.PARAMRESP_PARAM), "value"),
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
            return [text, text, text, text, None]

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
        print("1")
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
        print("2")
        return [
            "not_implemented",
            wcc.Graph(figure=scatterplot.figure),
            "not_implemented",
            wcc.Graph(figure=corrfig.figure),
            param,
        ]
