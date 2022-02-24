import webviz_core_components as wcc
from dash import dash_table, html


def uncertainty_table_layout(
    uuid: str,
) -> html.Div:
    """Layout for the uncertainty table dialog"""
    return html.Div(
        children=[
            wcc.FlexBox(
                children=[
                    html.Label(
                        className="webviz-structunc-uncertainty-table-label",
                        children="Statistics for well: ",
                        id={"id": uuid, "element": "label"},
                    ),
                    html.Button(
                        "Recalculate",
                        className="webviz-structunc-uncertainty-table-apply-btn",
                        id={"id": uuid, "element": "apply-button"},
                    ),
                ]
            ),
            dash_table.DataTable(
                id={"id": uuid, "element": "table"},
                columns=[
                    {"id": "Surface name", "name": "Surface name", "selectable": False},
                    {"id": "Ensemble", "name": "Ensemble", "selectable": False},
                    {"id": "Calculation", "name": "Calculation", "selectable": False},
                    {"id": "Pick no", "name": "Pick no", "selectable": False},
                    {
                        "id": "TVD",
                        "name": "TVD (MSL)",
                        "selectable": False,
                    },
                    {
                        "id": "MD",
                        "name": "MD (RKB)",
                        "selectable": False,
                    },
                ],
                style_header={
                    "opacity": 0.5,
                },
                style_filter={
                    "opacity": 0.5,
                },
                style_data_conditional=[
                    {
                        "if": {"column_id": "Surface name"},
                        "textAlign": "left",
                        "width": "15%",
                    },
                    {
                        "if": {"column_id": "Ensemble"},
                        "textAlign": "left",
                        "width": "15%",
                    },
                    {
                        "if": {"column_id": "Calculation"},
                        "textAlign": "left",
                        "width": "10%",
                    },
                    {
                        "if": {"filter_query": '{Calculation} = "Mean"'},
                        "backgroundColor": "rgba(0,177,106,0.3)",
                    },
                ],
                sort_action="native",
                filter_action="native",
            ),
        ],
    )
