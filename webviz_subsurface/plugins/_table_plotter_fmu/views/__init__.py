import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc


def main_view(parent) -> html.Div:
    return wcc.FlexBox(
        children=[
            html.Div(style={"flex": 1}, children=[sidebar_view(parent)]),
            html.Div(style={"flex": 5}, children=[plot_view(parent)]),
        ]
    )


def sidebar_view(parent) -> wcc.FlexBox:
    return html.Div([selectors(parent)])


def plot_view(parent) -> html.Div:
    return html.Div(dcc.Graph(id=parent.uuid("graph")))


def selectors(parent) -> html.Div:
    return html.Div(
        children=[ensemble_selector(parent), x_selector(parent), y_selector(parent)]
    )


def ensemble_selector(parent, flex=1) -> html.Div:
    return html.Div(
        style={"flex": flex},
        children=[
            html.Label("Ensemble"),
            dcc.Dropdown(
                id={"id": parent.uuid("selectors"), "attribute": "ensemble"},
                options=[
                    {"label": ens, "value": ens}
                    for ens in parent.tablemodel.ensemble_names()
                ],
                value=parent.tablemodel.ensemble_names()[0],
                clearable=False,
            ),
        ],
    )


def x_selector(parent, flex=1) -> html.Div:
    return html.Div(
        style={"flex": flex},
        children=[
            html.Label("Data for x-axis"),
            dcc.Dropdown(
                id={"id": parent.uuid("selectors"), "attribute": "x_selector"},
                clearable=False,
            ),
        ],
    )


def y_selector(parent, flex=1) -> html.Div:
    return html.Div(
        style={"flex": flex},
        children=[
            html.Label("Data for y-axis"),
            dcc.Dropdown(
                id={"id": parent.uuid("selectors"), "attribute": "y_selector"},
                clearable=False,
            ),
        ],
    )