from typing import Callable

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import webviz_core_components as wcc
from dash import Input, Output, State, callback, callback_context, html
from dash.exceptions import PreventUpdate

from ..utils.table_and_figure_utils import create_data_table, create_table_columns


def fipfile_qc_controller(get_uuid: Callable, disjoint_set_df: pd.DataFrame) -> None:
    @callback(
        Output(get_uuid("main-fipqc"), "children"),
        Input(get_uuid("selections"), "data"),
        Input({"id": get_uuid("main-fipqc"), "element": "display-option"}, "value"),
        State(get_uuid("page-selected"), "data"),
    )
    def _update_page_fipfileqc(
        selections: dict, display_option: str, page_selected: str
    ) -> html.Div:
        ctx = callback_context.triggered[0]

        if page_selected != "fipqc":
            raise PreventUpdate

        df = disjoint_set_df[["SET", "FIPNUM", "REGION", "ZONE", "REGZONE"]]

        selections = selections[page_selected]
        if not "display-option" in ctx["prop_id"]:
            if not selections["update"]:
                raise PreventUpdate

        for filt, values in selections["filters"].items():
            df = df.loc[df[filt].isin(values)]

        if selections["Group table"] and display_option == "table":
            df["FIPNUM"] = df["FIPNUM"].astype(str)
            df = df.groupby(["SET"]).agg(lambda x: ", ".join(set(x))).reset_index()

        df = df.sort_values(by=["SET"])

        if display_option == "table":
            return html.Div(
                children=create_data_table(
                    columns=create_table_columns(df.columns),
                    data=df.to_dict("records"),
                    height="82vh",
                    table_id={"table_id": "disjointset-info"},
                    style_cell_conditional=[
                        {"if": {"column_id": ["SET", "FIPNUM"]}, "width": "10%"},
                        {"if": {"column_id": ["ZONE", "REGION"]}, "width": "20%"},
                    ],
                    style_cell={
                        "whiteSpace": "normal",
                        "textAlign": "left",
                        "height": "auto",
                    },
                ),
            )

        df["FIPNUM"] = df["FIPNUM"].astype(str)
        return html.Div(
            [
                create_heatmap(df=df, y="ZONE", x="REGION"),
                create_heatmap(df=df, y="ZONE", x="FIPNUM"),
                create_heatmap(df=df, y="REGION", x="FIPNUM"),
            ]
        )


def create_heatmap(df: pd.DataFrame, y: str, x: str) -> wcc.Graph:
    """Create heatmap"""
    unique_y = df[y].unique()
    unique_x = sorted(df[x].unique(), key=int if x == "FIPNUM" else None)
    data = []
    for y_elm in unique_y:
        set_list = []
        for x_elm in unique_x:
            set_idx = df.loc[(df[y] == y_elm) & (df[x] == x_elm), "SET"]
            set_list.append(set_idx.iloc[0] if not set_idx.empty else None)
        data.append(set_list)

    return wcc.Graph(
        config={"displayModeBar": False},
        style={"height": "28vh"},
        figure=go.Figure(
            data=go.Heatmap(
                z=data,
                x=unique_x,
                y=unique_y,
                colorscale=(
                    px.colors.qualitative.Safe
                    + px.colors.qualitative.T10
                    + px.colors.qualitative.Set1
                ),
                showscale=False,
                hovertemplate="SET: %{z} <br>"
                + f"{x}: %{{x}} <br>"
                + f"{y}: %{{y}} <extra></extra>",
            )
        )
        .update_layout(
            margin={"l": 20, "r": 20, "t": 20, "b": 20}, plot_bgcolor="white"
        )
        .update_xaxes(title_text=x, tickangle=45, ticks="outside", **axis_variables())
        .update_yaxes(title_text=y, **axis_variables()),
    )


def axis_variables() -> dict:
    return {"showline": True, "linewidth": 2, "linecolor": "black", "mirror": True}
