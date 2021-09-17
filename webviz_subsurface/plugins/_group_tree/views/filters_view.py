from typing import Callable

import webviz_core_components as wcc


def filters_layout(get_uuid: Callable) -> wcc.Selectors:
    """Descr"""
    filters_uuid = get_uuid("filters")
    return wcc.Selectors(
        id=get_uuid("filters_layout"),
        label="Filters",
        children=[
            wcc.SelectWithLabel(
                label="Prod/Inj/Obs",
                id={"id": filters_uuid, "element": "prod_inj_obs"},
                options=[
                    {"label": "Production", "value": "prod"},
                    {"label": "Injection", "value": "inj"},
                    {"label": "Observation", "value": "obs"},
                ],
                value=["prod", "inj", "obs"],
                multi=True,
                size=3,
            )
        ],
    )
