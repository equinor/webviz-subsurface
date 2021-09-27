from typing import Callable, Dict, List, Optional

import webviz_core_components as wcc
from dash import dcc, html

from ..models import PropertyStatisticsModel
from .property_delta_view import property_delta_view
from .property_qc_view import property_qc_view
from .property_response_view import property_response_view


def main_view(
    get_uuid: Callable,
    property_model: PropertyStatisticsModel,
    vector_options: List[Dict],
    surface_folders: Optional[Dict] = None,
) -> dcc.Tabs:
    tabs = [
        make_tab(
            label="Property QC",
            children=property_qc_view(get_uuid=get_uuid, property_model=property_model),
        )
    ]
    if len(property_model.ensembles) > 1:
        tabs.append(
            make_tab(
                label="AHM impact on property",
                children=property_delta_view(
                    get_uuid=get_uuid,
                    property_model=property_model,
                    surface_folders=surface_folders,
                ),
            )
        )
    tabs.append(
        make_tab(
            label="Property impact on simulation profiles",
            children=property_response_view(
                get_uuid=get_uuid,
                property_model=property_model,
                vector_options=vector_options,
                surface_folders=surface_folders,
            ),
        ),
    )

    return html.Div(
        id=get_uuid("layout"),
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
