import dash_html_components as html
import dash_core_components as dcc
import dash_table
import webviz_core_components as wcc


def distributions_main_layout(uuid: str) -> html.Div:
    return html.Div(
        children=[
            html.Div(
                id={"id": uuid, "page": "Custom plotting"},
                style={"display": "block"},
                children=custom_plotting_layout(uuid),
            ),
            html.Div(
                id={"id": uuid, "page": "1 plot / 1 table"},
                style={"display": "none"},
                children=one_plot_one_table_layout(uuid),
            ),
            html.Div(
                id={"id": uuid, "page": "Plots per zone/region"},
                style={"display": "none"},
                children=plots_per_zone_region_layout(uuid),
            ),
            html.Div(
                id={"id": uuid, "page": "Cumulative mean/p10/p90"},
                style={"display": "none"},
                children=cumulative_plot_layout(uuid),
            ),
        ]
    )


def cumulative_plot_layout(uuid: str) -> html.Div:
    return html.Div(
        className="framed",
        style={"height": "91vh"},
        children=[
            wcc.Graph(
                id={"id": uuid, "element": "plot", "page": "Cumulative mean/p10/p90"},
                config={"displayModeBar": False},
                style={"height": "85vh"},
            )
        ],
    )


def custom_plotting_layout(uuid: str) -> html.Div:
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
                id={"id": uuid, "wrapper": "graph", "page": "Custom plotting"},
                style={"display": "inline"},
                children=wcc.Graph(
                    id={"id": uuid, "element": "graph", "page": "Custom plotting"},
                    config={"displayModeBar": False},
                    style={"height": "85vh"},
                ),
            ),
            html.Div(
                id={"id": uuid, "wrapper": "table", "page": "Custom plotting"},
                style={"display": "none"},
                children=dash_table.DataTable(
                    id={"id": uuid, "element": "table", "page": "Custom plotting"},
                    sort_action="native",
                    filter_action="native",
                ),
            ),
        ],
    )


def one_plot_one_table_layout(uuid: str) -> html.Div:
    return html.Div(
        children=[
            html.Div(
                className="webviz-inplace-vol-framed",
                style={"height": "44vh"},
                children=wcc.Graph(
                    id={
                        "id": uuid,
                        "element": "graph",
                        "page": "1 plot / 1 table",
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
                        "page": "1 plot / 1 table",
                    },
                    page_size=16,
                    sort_action="native",
                    filter_action="native",
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
                                        "piechart": "per_zone",
                                        "page": "Plots per zone/region",
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
                                        "barchart": "per_zone",
                                        "page": "Plots per zone/region",
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
                                    "piechart": "per_region",
                                    "page": "Plots per zone/region",
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
                                    "barchart": "per_region",
                                    "page": "Plots per zone/region",
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
