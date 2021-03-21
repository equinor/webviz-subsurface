from typing import List, Dict, Union, Optional

import dash_core_components as dcc
import dash_html_components as html


def plot_options_view(get_uuid) -> html.Div:
    return html.Div(
        className="framed",
        style={"height": "600px", "fontSize": "0.8em"},
        children=[
            html.H5("Plot options"),
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
                value=None,
            ),
            dropdown_for_plotly_layout(
                uuid=get_uuid("plotly_layout"),
                layout_attribute="xaxis_autorange",
                title="X-axis direction",
                options=[
                    {"value": True, "label": "normal"},
                    {"value": "reversed", "label": "reversed"},
                ],
                value=True,
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
                value=None,
            ),
            dropdown_for_plotly_layout(
                uuid=get_uuid("plotly_layout"),
                layout_attribute="yaxis_autorange",
                title="Y-axis direction",
                options=[
                    {"value": True, "label": "normal"},
                    {"value": "reversed", "label": "reversed"},
                ],
                value=True,
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
                id={
                    "id": uuid,
                    "layout_attribute": layout_attribute,
                },
                options=options,
                value=value,
                clearable=False,
                placeholder=placeholder,
            ),
        ],
    )