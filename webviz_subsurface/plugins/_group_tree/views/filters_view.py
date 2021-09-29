from typing import Callable

import webviz_core_components as wcc


def filters_layout(get_uuid: Callable) -> wcc.Selectors:
    """The filters part of the menu"""
    filters_uuid = get_uuid("filters")
    return wcc.Selectors(
        id=get_uuid("filters_layout"),
        label="Filters",
        children=[
            wcc.SelectWithLabel(
                label="Prod/Inj/Other",
                id={"id": filters_uuid, "element": "prod_inj_other"},
                options=[
                    {"label": "Production", "value": "prod"},
                    {"label": "Injection", "value": "inj"},
                    {"label": "Other", "value": "other"},
                ],
                value=["prod", "inj", "other"],
                multi=True,
                size=3,
            )
        ],
    )
