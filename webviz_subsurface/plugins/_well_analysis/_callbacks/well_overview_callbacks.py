from typing import Callable, Dict, List

import webviz_core_components as wcc
from dash import ALL, Dash, Input, Output, State, callback, callback_context, no_update
from webviz_config import WebvizConfigTheme

from .._ensemble_data import EnsembleWellAnalysisData
from .._figures import WellOverviewChart
from .._layout import ClientsideStoreElements, WellOverviewLayoutElements


def well_overview_callbacks(
    app: Dash,
    get_uuid: Callable,
    data_models: Dict[str, EnsembleWellAnalysisData],
    theme: WebvizConfigTheme,
) -> None:
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
            return "bar"

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

    @callback(
        Output(
            {
                "id": get_uuid(WellOverviewLayoutElements.CHARTTYPE_SETTINGS),
                "charttype": ALL,
            },
            "style",
        ),
        Input(get_uuid(ClientsideStoreElements.WELL_OVERVIEW_CHART_SELECTED), "data"),
        State(
            {
                "id": get_uuid(WellOverviewLayoutElements.CHARTTYPE_SETTINGS),
                "charttype": ALL,
            },
            "id",
        ),
    )
    def _display_charttype_settings(
        chart_selected: str, charttype_settings_ids: list
    ) -> list:
        return [
            {"display": "block"}
            if settings_id["charttype"] == chart_selected
            else {"display": "none"}
            for settings_id in charttype_settings_ids
        ]

    @app.callback(
        Output(get_uuid(WellOverviewLayoutElements.GRAPH), "children"),
        Input(get_uuid(WellOverviewLayoutElements.ENSEMBLES), "value"),
        Input(
            {
                "id": get_uuid(WellOverviewLayoutElements.CHARTTYPE_SETTINGS),
                "chartype": ALL,
            },
            "value",
        ),
        Input(get_uuid(WellOverviewLayoutElements.SUMVEC), "value"),
        Input(get_uuid(ClientsideStoreElements.WELL_OVERVIEW_CHART_SELECTED), "data"),
    )
    def _update_graph(
        ensembles: List[str], settings: List[str], sumvec: str, chart_selected: str
    ) -> List[wcc.Graph]:
        """Updates the graph according to the selected chart type"""
        print(f"update_graph: {chart_selected}")
        print(settings)
        figure = WellOverviewChart(
            ensembles, data_models, sumvec, chart_selected, [], theme
        )

        if chart_selected == "area":
            return ["Stacked area chart not implemented"]

        return [wcc.Graph(style={"height": "87vh"}, figure=figure.figure)]


def update_relevant_components(id_list: list, update_info: List[dict]) -> list:
    output_id_list = [no_update] * len(id_list)
    for elm in update_info:
        for idx, x in enumerate(id_list):
            if all(x[key] == value for key, value in elm["conditions"].items()):
                output_id_list[idx] = elm["new_value"]
                break
    return output_id_list
