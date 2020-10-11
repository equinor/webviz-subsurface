import dash_html_components as html
import dash_core_components as dcc

from .property_qc_view import property_qc_view
from .property_delta_view import property_delta_view
from .property_response_view import property_response_view


def main_view(parent) -> dcc.Tabs:
    tabs = [
        make_tab(
            label="Property QC",
            children=property_qc_view(parent=parent),
        )
    ]
    if len(parent.pmodel.ensembles) > 1:
        tabs.append(
            make_tab(
                label="AHM impact on property",
                children=property_delta_view(parent=parent),
            )
        )
    tabs.append(
        make_tab(
            label="Property impact on simulation profiles",
            children=property_response_view(parent=parent),
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
