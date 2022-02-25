from typing import Callable, Dict, List

import pandas as pd
import webviz_core_components as wcc
from dash import ALL, Dash, Input, Output, State, callback, callback_context, no_update

from webviz_subsurface._figures import create_figure

from .._ensemble_data import EnsembleWellAnalysisData
from .._figures import WellProdBarChart
from .._layout import ClientsideStoreElements, WellOverviewLayoutElements


def well_overview_callbacks(
    app: Dash, get_uuid: Callable, data_models: Dict[str, EnsembleWellAnalysisData]
) -> None:
    print("well overview callbacks")

    @app.callback(
        Output(get_uuid(ClientsideStoreElements.WELL_OVERVIEW_CHART_SELECTED), "data"),
        Input(
            {
                "id": get_uuid(WellOverviewLayoutElements.CHARTTYPE_BUTTON),
                "button": ALL,
            },
            "n_clicks",
        ),
        State(
            {
                "id": get_uuid(WellOverviewLayoutElements.CHARTTYPE_BUTTON),
                "button": ALL,
            },
            "id",
        ),
    )
    def _update_chart_selected(_apply_click: int, button_ids: list) -> str:
        """Stores the selected chart type in ClientsideStoreElements.WELL_OVERVIEW_CHART_SELECTED"""
        ctx = callback_context.triggered[0]

        # handle initial callback
        if ctx["prop_id"] == ".":
            return "barchart"

        for button_id in button_ids:
            if button_id["button"] in ctx["prop_id"]:
                return button_id["button"]

    @callback(
        Output(
            {
                "id": get_uuid(WellOverviewLayoutElements.CHARTTYPE_BUTTON),
                "button": ALL,
            },
            "style",
        ),
        Input(get_uuid(ClientsideStoreElements.WELL_OVERVIEW_CHART_SELECTED), "data"),
        State(
            {
                "id": get_uuid(WellOverviewLayoutElements.CHARTTYPE_BUTTON),
                "button": ALL,
            },
            "id",
        ),
    )
    def _update_button_style(chart_selected: str, button_ids: list) -> list:

        button_styles = {
            button["button"]: {"background-color": "#E8E8E8"} for button in button_ids
        }
        button_styles[chart_selected] = {"background-color": "#7393B3", "color": "#fff"}

        return update_relevant_components(
            id_list=button_ids,
            update_info=[
                {
                    "new_value": style,
                    "conditions": {"button": button},
                }
                for button, style in button_styles.items()
            ],
        )

    @app.callback(
        Output(get_uuid(WellOverviewLayoutElements.GRAPH), "children"),
        Input(get_uuid(WellOverviewLayoutElements.ENSEMBLES), "value"),
        Input(get_uuid(WellOverviewLayoutElements.OVERLAY_BARS), "value"),
        Input(get_uuid(WellOverviewLayoutElements.SUMVEC), "value"),
        Input(get_uuid(ClientsideStoreElements.WELL_OVERVIEW_CHART_SELECTED), "data"),
    )
    def _update_graph(
        ensembles: List[str], overlay_bars: str, sumvec: str, chart_selected: str
    ) -> List[wcc.Graph]:
        """Updates the graph according to the selected chart type"""
        print(f"update_graph: {chart_selected}")
        dataframes = []
        for _, data_model in data_models.items():
            dataframes.append(data_model.get_dataframe_melted(sumvec))
        df = pd.concat(dataframes)
        df.to_csv("/private/olind/webviz/melted.csv")

        if chart_selected == "barchart":
            figure = WellProdBarChart(
                ensembles,
                data_models,
                sumvec,
                "overlay_bars" in overlay_bars,
            )
            return [wcc.Graph(figure={"data": figure.traces, "layout": figure.layout})]

        if chart_selected == "piechart":
            piefig = create_figure(
                plot_type="pie",
                data_frame=df,
                values=sumvec,
                names="WELL",
                title=sumvec
                # color_discrete_sequence=self.colorway,
            )
            print(piefig)
            return [wcc.Graph(figure=piefig)]
            # return ["Pie chart not implemented"]
        if chart_selected == "areachart":
            return ["Stacked area chart not implemented"]

        raise ValueError(f"Chart type {chart_selected} does not exist")


def update_relevant_components(id_list: list, update_info: List[dict]) -> list:
    output_id_list = [no_update] * len(id_list)
    for elm in update_info:
        for idx, x in enumerate(id_list):
            if all(x[key] == value for key, value in elm["conditions"].items()):
                output_id_list[idx] = elm["new_value"]
                break
    return output_id_list
