from enum import Enum
from typing import Dict, List, Optional
from typing import Callable

from dash import html

import webviz_core_components as wcc

from ..models import UpscalingQCModel


class PlotTypes(str, Enum):
    HISTOGRAM = "Histogram"


def sidebar(get_uuid: Callable, qc_model: UpscalingQCModel) -> html.Div:
    selectors = [
        _make_selector(
            uuid={"type": get_uuid("selector"), "value": selector},
            label=selector,
            values=qc_model.get_unique_selector_values(selector),
        )
        for selector in qc_model.selectors
    ]
    return html.Div(
        [
            wcc.Selectors(
                label="Plot:",
                children=[
                    wcc.Dropdown(
                        id=get_uuid("plot-type"),
                        options=[{"value": val, "label": val} for val in PlotTypes],
                        value=PlotTypes.HISTOGRAM,
                        label="Plot type",
                        clearable=False
                    ),
                    wcc.Dropdown(
                        id=get_uuid("x"),
                        options=[
                            {"value": val, "label": val} for val in qc_model.properties
                        ],
                        value=qc_model.properties[0],
                        label="X",
                        clearable=False
                    ),
                    wcc.Dropdown(
                        id=get_uuid("group"),
                        options=[
                            {"value": val, "label": val} for val in qc_model.selectors
                        ],
                        value=None,
                        label="Group by",
                    ),
                    wcc.Dropdown(
                        id=get_uuid("color"),
                        options=[
                            {"value": val, "label": val} for val in qc_model.selectors
                        ],
                        value=None,
                        label="Color",
                    ),
                ],
            ),
            html.Div(selectors),
        ]
    )


def _make_selector(
    uuid: Dict[str, str], label: str, values: List[str], default: Optional[str] = None
) -> html.Div:
    return wcc.SelectWithLabel(
        id=uuid,
        label=label,
        options=[{"value": value, "label": value} for value in values],
        value=default if default is not None else values,
        multi=True,
        size=min(len(values), 8),
    )
