import dash_html_components as html
import dash_core_components as dcc
import dash_table
import webviz_core_components as wcc


def distributions_main_layout(uuid: str) -> html.Div:
    return html.Div(
        children=[
            html.Div(
                className="framed",
                id={"id": uuid, "layout": "1x1"},
                style={"display": "block"},
                children=distributions_main_layout_1x1(uuid),
            ),
            html.Div(
                id={"id": uuid, "layout": "2x1"},
                style={"display": "none"},
                children=distributions_main_layout_2x1(uuid),
            ),
        ]
    )


def distributions_main_layout_1x1(uuid: str) -> html.Div:
    return html.Div(
        children=[
            html.Div(
                children=dcc.RadioItems(
                    id={"id": uuid, "element": "plot-table-select"},
                    options=[
                        {
                            "label": "Plot",
                            "value": "plot",
                        },
                        {"label": "Table", "value": "table"},
                    ],
                    value="plot",
                    labelStyle={
                        "display": "inline-block",
                        "margin": "5px",
                    },
                ),
            ),
            html.Div(
                id={"id": uuid, "element": "graph-wrapper", "layout": "1x1"},
                style={"display": "inline"},
                children=wcc.Graph(
                    id={"id": uuid, "element": "graph", "layout": "1x1"},
                    config={"displayModeBar": False},
                    style={"height": "85vh"},
                ),
            ),
            html.Div(
                id={"id": uuid, "element": "table-wrapper", "layout": "1x1"},
                style={"display": "none"},
                children=dash_table.DataTable(
                    id={"id": uuid, "element": "table", "layout": "1x1"},
                    sort_action="native",
                    filter_action="native",
                ),
            ),
        ]
    )


def distributions_main_layout_2x1(uuid: str) -> html.Div:
    return html.Div(
        children=[
            html.Div(
                className="webviz-inplace-vol-framed",
                style={"height": "44vh"},
                children=[
                    html.Div(
                        id={"id": uuid, "wrapper": "graph", "layout": "2x1"},
                        children=wcc.Graph(
                            id={"id": uuid, "element": "graph", "layout": "2x1"},
                            config={"displayModeBar": False},
                            style={"height": "44vh"},
                        ),
                    ),
                    html.Div(
                        id={"id": uuid, "wrapper": "per-zone", "layout": "2x1_per"},
                        style={"display": "none"},
                        children=wcc.FlexBox(
                            children=[
                                html.Div(
                                    style={"flex": 1},
                                    children=wcc.Graph(
                                        id={
                                            "id": uuid,
                                            "element": "pie_chart",
                                            "layout": "per_zone",
                                        },
                                        config={"displayModeBar": False},
                                        style={"height": "44vh"},
                                    ),
                                ),
                                html.Div(
                                    style={"flex": 3},
                                    children=wcc.Graph(
                                        id={
                                            "id": uuid,
                                            "element": "bar_chart",
                                            "layout": "per_zone",
                                        },
                                        config={"displayModeBar": False},
                                        style={"height": "44vh"},
                                    ),
                                ),
                            ]
                        ),
                    ),
                ],
            ),
            html.Div(
                className="webviz-inplace-vol-framed",
                style={"height": "44vh"},
                children=[
                    html.Div(
                        id={"id": uuid, "wrapper": "table", "layout": "2x1"},
                        children=dash_table.DataTable(
                            id={"id": uuid, "element": "table", "layout": "2x1"},
                            page_size=16,
                            sort_action="native",
                            filter_action="native",
                        ),
                    ),
                    html.Div(
                        id={
                            "id": uuid,
                            "wrapper": "per-region",
                            "layout": "2x1_per",
                        },
                        style={"display": "none"},
                        children=wcc.FlexBox(
                            children=[
                                html.Div(
                                    style={"flex": 1},
                                    children=wcc.Graph(
                                        id={
                                            "id": uuid,
                                            "element": "pie_chart",
                                            "layout": "per_region",
                                        },
                                        config={"displayModeBar": False},
                                        style={"height": "44vh"},
                                    ),
                                ),
                                html.Div(
                                    style={"flex": 3},
                                    children=wcc.Graph(
                                        id={
                                            "id": uuid,
                                            "element": "bar_chart",
                                            "layout": "per_region",
                                        },
                                        config={"displayModeBar": False},
                                        style={"height": "44vh"},
                                    ),
                                ),
                            ]
                        ),
                    ),
                ],
            ),
        ]
    )
