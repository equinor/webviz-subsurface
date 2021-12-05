from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import webviz_core_components as wcc
from dash import Dash, Input, Output

from ...._figures import BarChart
from .._business_logic import RftPlotterDataModel, correlate, filter_frame
from .._layout import LayoutElements


def paramresp_callbacks(
    app: Dash, get_uuid: Callable, datamodel: RftPlotterDataModel
) -> None:
    @app.callback(
        Output(get_uuid(LayoutElements.PARAMRESP_DATE), "options"),
        Output(get_uuid(LayoutElements.PARAMRESP_DATE), "value"),
        Input(get_uuid(LayoutElements.PARAMRESP_WELL), "value"),
    )
    def _update_date(well: str) -> Tuple[List[Dict[str, str]], str]:
        dates_in_well = datamodel.date_in_well(well)
        return [
            {"label": date, "value": date} for date in datamodel.date_in_well(well)
        ], dates_in_well[0]

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

        merged_df = rft_df.merge(param_df, on="REAL")

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

        return [
            "not_implemented",
            "not_implemented",
            "not_implemented",
            wcc.Graph(figure=corrfig.figure),
            param,
        ]
