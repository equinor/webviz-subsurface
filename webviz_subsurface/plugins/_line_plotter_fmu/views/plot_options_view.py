from typing import List, Dict, Union, Callable

import dash_core_components as dcc
import dash_html_components as html


def plot_options_view(get_uuid: Callable, initial_layout: Dict) -> html.Div:
    return html.Div(
        className="framed",
        style={"fontSize": "0.8em"},
        children=[
            html.H5("Plot options"),
            dcc.Checklist(
                id=get_uuid("plotly_uirevision"),
                options=[{"label": "Keep plot range and zoom", "value": "keep"}],
                labelStyle={"display": "block"},
                persistence=True,
                persistence_type="session",
            ),
            dropdown_for_plotly_layout(
                uuid=get_uuid("plotly_layout"),
                layout_attribute="xaxis_type",
                title="X-axis type",
                options=[
                    {"value": None, "label": "Automatic"},
                    {"value": "linear", "label": "Linear"},
                    {"value": "log", "label": "Log"},
                    {"value": "date", "label": "Date"},
                    {"value": "category", "label": "Category"},
                    {"value": "multicategory", "label": "Multicategory"},
                ],
                placeholder="automatic",
                value=initial_layout.get("xaxis", {}).get("type", None),
            ),
            dropdown_for_plotly_layout(
                uuid=get_uuid("plotly_layout"),
                layout_attribute="xaxis_autorange",
                title="X-axis direction",
                options=[
                    {"value": True, "label": "normal"},
                    {"value": "reversed", "label": "reversed"},
                ],
                value=initial_layout.get("xaxis", {}).get("autorange", True),
            ),
            dropdown_for_plotly_layout(
                uuid=get_uuid("plotly_layout"),
                layout_attribute="yaxis_type",
                title="Y-axis type",
                options=[
                    {"value": None, "label": "Automatic"},
                    {"value": "linear", "label": "Linear"},
                    {"value": "log", "label": "Log"},
                    {"value": "date", "label": "Date"},
                    {"value": "category", "label": "Category"},
                    {"value": "multicategory", "label": "Multicategory"},
                ],
                placeholder="automatic",
                value=initial_layout.get("yaxis", {}).get("type", None),
            ),
            dropdown_for_plotly_layout(
                uuid=get_uuid("plotly_layout"),
                layout_attribute="yaxis_autorange",
                title="Y-axis direction",
                options=[
                    {"value": True, "label": "normal"},
                    {"value": "reversed", "label": "reversed"},
                ],
                value=initial_layout.get("yaxis", {}).get("autorange", True),
            ),
        ],
    )


def dropdown_for_plotly_layout(
    uuid: str,
    layout_attribute: str,
    title: str,
    options: List[Dict],
    value: Union[List, str],
    flex: int = 1,
    placeholder: str = "Select...",
) -> html.Div:
    return html.Div(
        style={"flex": flex},
        children=[
            html.Label(title),
            dcc.Dropdown(
                style={"backgroundColor": "transparent"},
                id={
                    "id": uuid,
                    "layout_attribute": layout_attribute,
                },
                options=options,
                value=value,
                clearable=False,
                placeholder=placeholder,
                persistence=True,
                persistence_type="session",
            ),
        ],
    )
