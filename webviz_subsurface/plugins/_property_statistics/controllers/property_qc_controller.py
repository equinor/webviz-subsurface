from typing import Callable, List, Union

import webviz_core_components as wcc
from dash import ALL, Dash, Input, Output, dash_table

from ..models import PropertyStatisticsModel


def property_qc_controller(
    get_uuid: Callable, property_model: PropertyStatisticsModel, app: Dash
) -> None:
    @app.callback(
        Output(get_uuid("property-qc-wrapper"), "children"),
        Input({"id": get_uuid("ensemble-selector"), "tab": "qc"}, "value"),
        Input({"id": get_uuid("property-selector"), "tab": "qc"}, "value"),
        Input(
            {"id": get_uuid("filter-selector"), "tab": "qc", "selector": ALL},
            "value",
        ),
        Input(get_uuid("property-qc-plot-type"), "value"),
        Input(get_uuid("property-qc-axis-match"), "value"),
    )
    def _update_bars(
        ensembles: Union[str, List[str]],
        prop: str,
        selectors: list,
        plot_type: str,
        match_axis: List[str],
    ) -> Union[dash_table.DataTable, wcc.Graph]:
        ensembles = ensembles if isinstance(ensembles, list) else [ensembles]
        if plot_type == "table":
            columns, dframe = property_model.make_statistics_table(
                prop=prop, ensembles=ensembles, selector_values=selectors
            )
            return dash_table.DataTable(
                style_table={
                    "height": "75vh",
                    "overflow": "auto",
                    "fontSize": 15,
                },
                style_cell={"textAlign": "center"},
                style_cell_conditional=[
                    {"if": {"column_id": "label|"}, "textAlign": "left"}
                ],
                columns=columns,
                data=dframe,
                sort_action="native",
                filter_action="native",
                merge_duplicate_headers=True,
            )
        return wcc.Graph(
            id=get_uuid("property-qc-graph"),
            config={"displayModeBar": False},
            style={"height": "75vh"},
            figure=property_model.make_grouped_plot(
                prop=prop,
                ensembles=ensembles,
                selector_values=selectors,
                plot_type=plot_type,
                match_axis=bool(match_axis),
            ),
        )
