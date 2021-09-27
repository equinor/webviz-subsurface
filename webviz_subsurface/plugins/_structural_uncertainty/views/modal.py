from typing import List, Optional

import dash_bootstrap_components as dbc
from dash import html


def modal_layout(
    uuid: str,
    modal_id: str,
    title: str,
    body_children: List,
    footer: Optional[dbc.ModalFooter] = None,
    size: str = "sm",
) -> dbc.Modal:
    modalchildren = [
        dbc.ModalHeader(title),
        dbc.ModalBody(
            children=[*body_children],
        ),
    ]
    if footer:
        modalchildren.append(footer)
    return dbc.Modal(
        style={"marginTop": "20vh"},
        children=modalchildren,
        id={"id": uuid, "modal_id": modal_id, "element": "wrapper"},
        size=size,
    )


def open_modal_layout(uuid: str, modal_id: str, title: str) -> dbc.Button:
    return html.Div(
        children=html.Button(
            title,
            className="webviz-structunc-open-modal-btn",
            id={"id": uuid, "modal_id": modal_id, "element": "button-open"},
        ),
    )


def clear_all_apply_modal_buttons(
    uuid: str, modal_id: str, apply_disabled: bool = True
) -> dbc.ModalFooter:
    return dbc.ModalFooter(
        children=[
            html.Div(
                children=[
                    dbc.Button(
                        "Clear",
                        style={"padding": "0 20px"},
                        className="mr-1",
                        id={"id": uuid, "modal_id": modal_id, "element": "clear"},
                    ),
                    dbc.Button(
                        "All",
                        style={"padding": "0 20px"},
                        className="mr-1",
                        id={"id": uuid, "modal_id": modal_id, "element": "all"},
                    ),
                    dbc.Button(
                        "Apply",
                        style={"padding": "0 20px", "visibility": "hidden"}
                        if apply_disabled
                        else {"padding": "0 20px"},
                        className="mr-1",
                        id={"id": uuid, "modal_id": modal_id, "element": "apply"},
                    ),
                ]
            ),
        ]
    )
