from typing import Optional

import plotly.graph_objects as go
import webviz_core_components as wcc
from dash import html


def distributions_main_layout(uuid: str) -> html.Div:
    return html.Div(
        children=[
            html.Div(
                id={"id": uuid, "page": "custom"},
                style={"display": "block"},
            ),
            html.Div(
                id={"id": uuid, "page": "per_zr"},
                style={"display": "none"},
            ),
            html.Div(
                id={"id": uuid, "page": "conv"},
                style={"display": "none"},
            ),
        ]
    )


def table_main_layout(uuid: str) -> wcc.Frame:
    return html.Div(id={"id": uuid, "page": "table"})


def convergence_plot_layout(figure: go.Figure) -> wcc.Graph:
    return wcc.Graph(
        config={"displayModeBar": False},
        style={"height": "86vh"},
        figure=figure,
    )


def custom_plotting_layout(figure: go.Figure, tables: Optional[list]) -> html.Div:
    tables = tables if tables is not None else []
    return html.Div(
        children=[
            wcc.Graph(
                config={"displayModeBar": False},
                style={"height": "45vh" if tables else "86vh"},
                figure=figure,
            )
        ]
        + [html.Div(table, style={"margin-top": "20px"}) for table in tables]
    )


def plots_per_zone_region_layout(figures: list) -> list:
    height = "42vh" if len(figures) < 3 else "28vh"
    return html.Div(
        children=[
            html.Div(
                "Pie chart available if no 'Color by' is selected",
                style={"text-align": "right"},
            )
        ]
        + [
            wcc.FlexBox(
                style={"height": height},
                children=[
                    html.Div(
                        style={"flex": 3},
                        children=wcc.Graph(
                            config={"displayModeBar": False},
                            style={"height": height},
                            figure=barfig,
                        ),
                    ),
                    html.Div(
                        style={
                            "flex": 1,
                            "display": "block" if piefig else "none",
                        },
                        children=wcc.Graph(
                            config={"displayModeBar": False},
                            style={"height": height},
                            figure=piefig,
                        ),
                    ),
                ],
            )
            for piefig, barfig in figures
        ]
    )
