from typing import Callable, List

import webviz_core_components as wcc
from dash import Dash, Input, Output

from .._business_logic import filter_frame, RftPlotterDataModel
from .._layout import LayoutElements

# from ..figures.correlation_figure import CorrelationFigure


def paramresp_callbacks(app: Dash, get_uuid: Callable, data_model: RftPlotterDataModel):
    @app.callback(
        # Output(get_uuid(LayoutElements.PARAMRESP_RFT_VS_DEPTH_GRAPH), "children"),
        # Output(get_uuid(LayoutElements.PARAMRESP_RFT_VS_PARAM_GRAPH), "children"),
        Output(get_uuid(LayoutElements.PARAMRESP_RFT_CORR_GRAPH), "children"),
        # Output(get_uuid(LayoutElements.PARAMRESP_PARAM_CORR_GRAPH), "children"),
        Input(get_uuid(LayoutElements.PARAMRESP_ENSEMBLE), "value"),
        Input(get_uuid(LayoutElements.PARAMRESP_WELL), "value"),
        Input(get_uuid(LayoutElements.PARAMRESP_DATE), "value"),
        Input(get_uuid(LayoutElements.PARAMRESP_ZONE), "value"),
        Input(get_uuid(LayoutElements.PARAMRESP_PARAM), "value"),
    )
    def _update_graphs(
        ensemble: str,
        well: str,
        date: str,
        zone: str,
        param: str,
    ) -> List[wcc.Graph]:
        """
        Main callback to update plots.
        """
        print("update graphs triggered")
        df_filtered = filter_frame(
            data_model.ertdatadf,
            {
                "ENSEMBLE": ensemble,
                "WELL": well,
                "DATE": date,
                "ZONE": zone,
            },
        )
        df_filtered.to_csv("/private/olind/webviz/df_filtered.csv")
        # rft_corr = datamodel.calc_rft_correlations(ensemble, well, date, zone, param)

        return [wcc.Graph()]
