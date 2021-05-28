import dash_html_components as html
import dash_core_components as dcc
import dash_table
import webviz_core_components as wcc


def distributions_main_layout(uuid: str, volumemodel) -> html.Div:
    return html.Div(
        children=[
            html.Div(
                id={"id": uuid, "page": "custom"},
                style={"display": "block"},
                children=custom_plotting_layout(uuid, volumemodel),
            ),
            html.Div(
                id={"id": uuid, "page": "1p1t"},
                style={"display": "none"},
                children=one_plot_one_table_layout(uuid, volumemodel),
            ),
            html.Div(
                id={"id": uuid, "page": "per_zr"},
                style={"display": "none"},
                children=plots_per_zone_region_layout(uuid),
            ),
            html.Div(
                id={"id": uuid, "page": "conv"},
                style={"display": "none"},
                children=convergence_plot_layout(uuid),
            ),
        ]
    )


def convergence_plot_layout(uuid: str) -> html.Div:
    return html.Div(
        className="framed",
        style={"height": "91vh"},
        children=[
            wcc.Graph(
                id={"id": uuid, "element": "plot", "page": "conv"},
                config={"displayModeBar": False},
                style={"height": "85vh"},
            )
        ],
    )


def custom_plotting_layout(uuid: str, volumemodel) -> html.Div:
    return html.Div(
        className="framed",
        style={"height": "91vh"},
        children=[
            html.Div(
                children=dcc.RadioItems(
                    id={"id": uuid, "element": "plot-table-select"},
                    options=[
                        {
                            "label": "Plot",
                            "value": "graph",
                        },
                        {"label": "Table", "value": "table"},
                    ],
                    value="graph",
                    labelStyle={
                        "display": "inline-block",
                        "margin": "5px",
                    },
                ),
            ),
            html.Div(
                id={"id": uuid, "wrapper": "graph", "page": "custom"},
                style={"display": "inline"},
                children=wcc.Graph(
                    id={"id": uuid, "element": "graph", "page": "custom"},
                    config={"displayModeBar": False},
                    style={"height": "85vh"},
                ),
            ),
            html.Div(
                id={"id": uuid, "wrapper": "table", "page": "custom"},
                style={"display": "none"},
                children=dash_table.DataTable(
                    id={"id": uuid, "element": "table", "page": "custom"},
                    sort_action="native",
                    filter_action="native",
                    style_cell_conditional=[
                        {"if": {"column_id": c}, "textAlign": "left"}
                        for c in volumemodel.selectors + ["Response"]
                    ],
                ),
            ),
        ],
    )


def one_plot_one_table_layout(uuid: str, volumemodel) -> html.Div:
    return html.Div(
        children=[
            html.Div(
                className="webviz-inplace-vol-framed",
                style={"height": "44vh"},
                children=wcc.Graph(
                    id={
                        "id": uuid,
                        "element": "graph",
                        "page": "1p1t",
                    },
                    config={"displayModeBar": False},
                    style={"height": "44vh"},
                ),
            ),
            html.Div(
                className="webviz-inplace-vol-framed",
                style={"height": "44vh"},
                children=dash_table.DataTable(
                    id={
                        "id": uuid,
                        "element": "table",
                        "page": "1p1t",
                    },
                    page_size=16,
                    sort_action="native",
                    filter_action="native",
                    style_cell_conditional=[
                        {"if": {"column_id": c}, "textAlign": "left"}
                        for c in volumemodel.selectors + ["Response"]
                    ],
                ),
            ),
        ]
    )


def plots_per_zone_region_layout(uuid: str) -> html.Div:
    return html.Div(
        children=[
            html.Div(
                className="webviz-inplace-vol-framed",
                style={"height": "44vh"},
                children=[
                    wcc.FlexBox(
                        children=[
                            html.Div(
                                style={"flex": 1},
                                children=wcc.Graph(
                                    id={
                                        "id": uuid,
                                        "chart": "pie",
                                        "selector": "ZONE",
                                        "page": "per_zr",
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
                                        "chart": "bar",
                                        "selector": "ZONE",
                                        "page": "per_zr",
                                    },
                                    config={"displayModeBar": False},
                                    style={"height": "44vh"},
                                ),
                            ),
                        ]
                    ),
                ],
            ),
            html.Div(
                className="webviz-inplace-vol-framed",
                style={"height": "44vh"},
                children=wcc.FlexBox(
                    children=[
                        html.Div(
                            style={"flex": 1},
                            children=wcc.Graph(
                                id={
                                    "id": uuid,
                                    "chart": "pie",
                                    "selector": "REGION",
                                    "page": "per_zr",
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
                                    "chart": "bar",
                                    "selector": "REGION",
                                    "page": "per_zr",
                                },
                                config={"displayModeBar": False},
                                style={"height": "44vh"},
                            ),
                        ),
                    ]
                ),
            ),
        ],
    )
