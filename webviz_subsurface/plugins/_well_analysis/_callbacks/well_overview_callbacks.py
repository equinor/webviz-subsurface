import datetime
from typing import Callable, Dict, List, Set, Union

import plotly.graph_objects as go
import webviz_core_components as wcc
from dash import ALL, Dash, Input, Output, State, callback, callback_context, no_update
from webviz_config import WebvizConfigTheme

from .._ensemble_well_analysis_data import EnsembleWellAnalysisData
from .._figures import WellOverviewFigure, format_well_overview_figure
from .._layout import ClientsideStoreElements, WellOverviewLayoutElements
from .._types import ChartType


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
            return ChartType.BAR.value

        for button_id in button_ids:
            if button_id["button"] in ctx["prop_id"]:
                return ChartType(button_id["button"]).value
        raise ValueError("Id not found")

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
        """Updates the styling of the chart type buttons, showing which chart type
        is currently selected.
        """
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
        """Display only the settings relevant for the currently selected chart type."""
        return [
            {"display": "block"}
            if settings_id["charttype"] == chart_selected
            else {"display": "none"}
            for settings_id in charttype_settings_ids
        ]

    @app.callback(
        Output(get_uuid(WellOverviewLayoutElements.GRAPH_FRAME), "children"),
        Input(get_uuid(WellOverviewLayoutElements.ENSEMBLES), "value"),
        Input(
            {
                "id": get_uuid(WellOverviewLayoutElements.CHARTTYPE_CHECKLIST),
                "charttype": ALL,
            },
            "value",
        ),
        Input(get_uuid(WellOverviewLayoutElements.SUMVEC), "value"),
        Input(get_uuid(WellOverviewLayoutElements.DATE), "value"),
        Input(get_uuid(ClientsideStoreElements.WELL_OVERVIEW_CHART_SELECTED), "data"),
        Input(get_uuid(WellOverviewLayoutElements.WELL_FILTER), "value"),
        Input(
            {
                "id": get_uuid(WellOverviewLayoutElements.WELL_ATTRIBUTES),
                "category": ALL,
            },
            "value",
        ),
        State(
            {
                "id": get_uuid(WellOverviewLayoutElements.CHARTTYPE_CHECKLIST),
                "charttype": ALL,
            },
            "id",
        ),
        State(
            {
                "id": get_uuid(WellOverviewLayoutElements.WELL_ATTRIBUTES),
                "category": ALL,
            },
            "id",
        ),
        State(get_uuid(WellOverviewLayoutElements.GRAPH), "figure"),
    )
    def _update_graph(
        ensembles: List[str],
        checklist_values: List[List[str]],
        sumvec: str,
        prod_after_date: Union[str, None],
        chart_selected: str,
        wells_selected: List[str],
        well_attr_selected: List[str],
        checklist_ids: List[Dict[str, str]],
        well_attr_ids: List[Dict[str, str]],
        current_fig_dict: dict,
    ) -> List[wcc.Graph]:
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-arguments
        """Updates the well overview graph with selected input (f.ex chart type)"""
        ctx = callback_context.triggered[0]["prop_id"].split(".")[0]

        settings = {
            checklist_id["charttype"]: checklist_values[i]
            for i, checklist_id in enumerate(checklist_ids)
        }
        well_attributes_selected: Dict[str, List[str]] = {
            well_attr_id["category"]: list(well_attr_selected[i])
            for i, well_attr_id in enumerate(well_attr_ids)
        }

        # Make set of wells that match the well_attributes
        # Well attributes that does not exist in one ensemble will be ignored
        wellattr_filtered_wells: Set[str] = set()
        for _, ens_data_model in data_models.items():
            wellattr_filtered_wells = wellattr_filtered_wells.union(
                ens_data_model.filter_on_well_attributes(well_attributes_selected)
            )
        # Take the intersection with wells_selected.
        # this way preserves the order in wells_selected and will not have duplicates
        filtered_wells = [
            well for well in wells_selected if well in wellattr_filtered_wells
        ]

        # If the event is a plot settings event, then we only update the formatting
        # and not the figure data
        chart_selected_type = ChartType(chart_selected)
        if current_fig_dict is not None and is_plot_settings_event(ctx, get_uuid):
            fig_dict = format_well_overview_figure(
                go.Figure(current_fig_dict),
                chart_selected_type,
                settings[chart_selected_type.value],
                sumvec,
                prod_after_date,
            )
        else:
            figure = WellOverviewFigure(
                ensembles,
                data_models,
                sumvec,
                datetime.datetime.strptime(prod_after_date, "%Y-%m-%d")
                if prod_after_date is not None
                else None,
                chart_selected_type,
                filtered_wells,
                theme,
            )

            fig_dict = format_well_overview_figure(
                figure.figure,
                chart_selected_type,
                settings[chart_selected_type.value],
                sumvec,
                prod_after_date,
            )

        return [
            wcc.Graph(
                id=get_uuid(WellOverviewLayoutElements.GRAPH),
                style={"height": "87vh"},
                figure=fig_dict,
            )
        ]


def is_plot_settings_event(ctx: str, get_uuid: Callable) -> bool:
    if get_uuid(WellOverviewLayoutElements.CHARTTYPE_CHECKLIST) in ctx:
        return True
    return False


def update_relevant_components(id_list: list, update_info: List[dict]) -> list:
    output_id_list = [no_update] * len(id_list)
    for elm in update_info:
        for idx, x in enumerate(id_list):
            if all(x[key] == value for key, value in elm["conditions"].items()):
                output_id_list[idx] = elm["new_value"]
                break
    return output_id_list
