from typing import TYPE_CHECKING

import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc

from .property_qc_view import property_qc_view
from .property_delta_view import property_delta_view
from .property_response_view import property_response_view

if TYPE_CHECKING:
    # pylint: disable=cyclic-import
    from ..property_statistics import PropertyStatistics


def main_view(parent: "PropertyStatistics") -> dcc.Tabs:
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
        children=wcc.Tabs(
            style={"width": "100%"},
            children=tabs,
        ),
    )


def make_tab(label: str, children: wcc.FlexBox) -> dcc.Tab:

    return wcc.Tab(
        label=label,
        children=children,
    )
