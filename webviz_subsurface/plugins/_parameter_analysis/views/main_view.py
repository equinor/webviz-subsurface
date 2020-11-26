import dash_html_components as html
import dash_core_components as dcc

from .parameter_qc_view import parameter_qc_view
from .parameter_response_view import parameter_response_view


def main_view(parent) -> dcc.Tabs:
    tabs = [
        make_tab(
            label="Parameter distributions",
            children=parameter_qc_view(parent=parent),
        )
    ]
    if parent.vmodel is not None:
        tabs.append(
            make_tab(
                label="Parameters impact on simulation profiles",
                children=parameter_response_view(parent=parent),
            )
        )

    return html.Div(
        id=parent.uuid("layout"),
        children=dcc.Tabs(
            style={"width": "100%"},
            persistence=True,
            children=tabs,
        ),
    )


def make_tab(label, children):
    tab_style = {
        "borderBottom": "1px solid #d6d6d6",
        "padding": "6px",
        "fontWeight": "bold",
    }

    tab_selected_style = {
        "borderTop": "1px solid #d6d6d6",
        "borderBottom": "1px solid #d6d6d6",
        "backgroundColor": "#007079",
        "color": "white",
        "padding": "6px",
    }
    return dcc.Tab(
        label=label,
        style=tab_style,
        selected_style=tab_selected_style,
        children=children,
    )
