import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_subsurface._models import InplaceVolumesModel


def distributions_main_layout(uuid: str, volumemodel: InplaceVolumesModel) -> html.Div:
    return html.Div(
        children=[
            html.Div(
                id={"id": uuid, "page": "custom"},
                style={"display": "block"},
                children=custom_plotting_layout(uuid),
            ),
            html.Div(
                id={"id": uuid, "page": "1p1t"},
                style={"display": "none"},
                children=one_plot_one_table_layout(uuid),
            ),
            html.Div(
                id={"id": uuid, "page": "per_zr"},
                style={"display": "none"},
                children=plots_per_zone_region_layout(uuid, volumemodel),
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


def custom_plotting_layout(uuid: str) -> html.Div:
    return html.Div(
        className="framed",
        style={"height": "91vh"},
        children=[
            html.Div(
                children=dcc.RadioItems(
                    id={"id": uuid, "element": "plot-table-select"},
                    options=[
                        {"label": "Plot", "value": "graph"},
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
                    id={"id": uuid, "element": "graph", "page": "1p1t"},
                    config={"displayModeBar": False},
                    style={"height": "44vh"},
                ),
            ),
            html.Div(
                className="webviz-inplace-vol-framed",
                style={"height": "44vh"},
                id={"id": uuid, "wrapper": "table", "page": "1p1t"},
            ),
        ]
    )


def plots_per_zone_region_layout(
    uuid: str, volumemodel: InplaceVolumesModel
) -> html.Div:
    selectors = [x for x in ["ZONE", "REGION", "FACIES"] if x in volumemodel.selectors]
    height = max(88 / len(selectors), 25)
    layout = []
    for selector in selectors:
        layout.append(
            html.Div(
                className="webviz-inplace-vol-framed",
                style={"height": f"{height}vh"},
                children=wcc.FlexBox(
                    children=[
                        html.Div(
                            style={"flex": 1},
                            children=wcc.Graph(
                                id={
                                    "id": uuid,
                                    "chart": "pie",
                                    "selector": selector,
                                    "page": "per_zr",
                                },
                                config={"displayModeBar": False},
                                style={"height": f"{height}vh"},
                            ),
                        ),
                        html.Div(
                            style={"flex": 3},
                            children=wcc.Graph(
                                id={
                                    "id": uuid,
                                    "chart": "bar",
                                    "selector": selector,
                                    "page": "per_zr",
                                },
                                config={"displayModeBar": False},
                                style={"height": f"{height}vh"},
                            ),
                        ),
                    ]
                ),
            )
        )

    return html.Div(layout)
