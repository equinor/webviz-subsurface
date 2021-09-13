from dash import html
import webviz_core_components as wcc


def tornado_main_layout(uuid: str) -> html.Div:
    return html.Div(
        id={"id": uuid, "page": "tornado"},
        style={"display": "block"},
        children=tornado_plots_layout(uuid),
    )


def tornado_plots_layout(uuid: str) -> html.Div:
    return html.Div(
        children=[
            wcc.Frame(
                color="white",
                highlight=False,
                style={"height": "44vh"},
                children=[
                    wcc.FlexBox(
                        children=[
                            html.Div(
                                style={"flex": 1},
                                children=wcc.Graph(
                                    id={
                                        "id": uuid,
                                        "element": "bulktornado",
                                        "page": "tornado",
                                    },
                                    config={"displayModeBar": False},
                                    style={"height": "42vh"},
                                ),
                            ),
                            html.Div(
                                style={"flex": 1},
                                children=wcc.Graph(
                                    id={
                                        "id": uuid,
                                        "element": "inplacetornado",
                                        "page": "tornado",
                                    },
                                    config={"displayModeBar": False},
                                    style={"height": "42vh"},
                                ),
                            ),
                        ]
                    )
                ],
            ),
            wcc.Frame(
                color="white",
                highlight=False,
                style={"height": "44vh"},
                children=html.Div(
                    id={"id": uuid, "wrapper": "table", "page": "tornado"},
                    style={"display": "block"},
                ),
            ),
        ]
    )
