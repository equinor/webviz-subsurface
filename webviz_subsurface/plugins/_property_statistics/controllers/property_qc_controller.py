from typing import Union, List, TYPE_CHECKING

import dash
from dash.dependencies import Input, Output, ALL
import dash_table
import webviz_core_components as wcc

if TYPE_CHECKING:
    # pylint: disable=cyclic-import
    from ..property_statistics import PropertyStatistics


def property_qc_controller(parent: "PropertyStatistics", app: dash.Dash) -> None:
    @app.callback(
        Output(parent.uuid("property-qc-wrapper"), "children"),
        Input({"id": parent.uuid("ensemble-selector"), "tab": "qc"}, "value"),
        Input({"id": parent.uuid("property-selector"), "tab": "qc"}, "value"),
        Input(
            {"id": parent.uuid("filter-selector"), "tab": "qc", "selector": ALL},
            "value",
        ),
        Input(parent.uuid("property-qc-plot-type"), "value"),
        Input(parent.uuid("property-qc-axis-match"), "value"),
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
            columns, dframe = parent.pmodel.make_statistics_table(
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
            id=parent.uuid("property-qc-graph"),
            config={"displayModeBar": False},
            style={"height": "75vh"},
            figure=parent.pmodel.make_grouped_plot(
                prop=prop,
                ensembles=ensembles,
                selector_values=selectors,
                plot_type=plot_type,
                match_axis=bool(match_axis),
            ),
        )
