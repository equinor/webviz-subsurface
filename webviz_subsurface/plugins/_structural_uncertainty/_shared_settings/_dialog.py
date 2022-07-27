from typing import List

import dash_bootstrap_components as dbc
import webviz_core_components as wcc
from dash import html


def dialog_layout(
    uuid: str,
    dialog_id: str,
    title: str,
    children: List,
    size: str = "sm",
) -> wcc.Dialog:

    return wcc.Dialog(
        # style={"marginTop": "20vh"},
        children=children,
        id={"id": uuid, "dialog_id": dialog_id, "element": "wrapper"},
        max_width=size,
        title=title,
        draggable=True,
    )


def open_dialog_layout(uuid: str, dialog_id: str, title: str) -> dbc.Button:
    return html.Div(
        children=html.Button(
            title,
            id={"id": uuid, "dialog_id": dialog_id, "element": "button-open"},
        ),
    )


def clear_all_apply_dialog_buttons(
    uuid: str, dialog_id: str, apply_disabled: bool = True
) -> html.Div:
    return html.Div(
        children=[
            dbc.Button(
                "Clear",
                style={"padding": "0 20px"},
                className="mr-1",
                id={"id": uuid, "dialog_id": dialog_id, "element": "clear"},
            ),
            dbc.Button(
                "All",
                style={"padding": "0 20px"},
                className="mr-1",
                id={"id": uuid, "dialog_id": dialog_id, "element": "all"},
            ),
            dbc.Button(
                "Apply",
                style={"padding": "0 20px", "visibility": "hidden"}
                if apply_disabled
                else {"padding": "0 20px"},
                className="mr-1",
                id={"id": uuid, "dialog_id": dialog_id, "element": "apply"},
            ),
        ]
    )
