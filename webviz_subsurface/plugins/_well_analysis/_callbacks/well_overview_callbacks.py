from typing import Callable, Dict, List

import webviz_core_components as wcc
from dash import Dash, Input, Output

from .._ensemble_data import EnsembleData
from .._figures import WellProdBarChart
from .._layout import WellOverviewLayoutElements


def well_overview_callbacks(
    app: Dash, get_uuid: Callable, data_models: Dict[str, EnsembleData]
) -> None:
    print("well overview callbacks")

    @app.callback(
        Output(get_uuid(WellOverviewLayoutElements.GRAPH), "children"),
        Input(get_uuid(WellOverviewLayoutElements.ENSEMBLES), "value"),
        Input(get_uuid(WellOverviewLayoutElements.OVERLAY_BARS), "value"),
        Input(get_uuid(WellOverviewLayoutElements.SUMVEC), "value"),
    )
    def _update_graph(
        ensembles: List[str], overlay_bars: str, sumvec: str
    ) -> List[wcc.Graph]:

        filter_out_startswith = "R_"
        figure = WellProdBarChart(
            ensembles,
            data_models,
            sumvec,
            "overlay_bars" in overlay_bars,
            filter_out_startswith,
        )
        return [
            wcc.Graph(
                style={"height": "87vh"},
                figure={"data": figure.traces, "layout": figure.layout},
            )
        ]
