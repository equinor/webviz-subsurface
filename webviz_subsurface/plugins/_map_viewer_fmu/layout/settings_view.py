from typing import Callable
from enum import Enum

from dash import html
import webviz_core_components as wcc


class ColorMapID(str, Enum):
    SELECT = "colormap-select"
    RANGE = "colormap-range"
    KEEP_RANGE = "colormap-keep-range"
    RESET_RANGE = "colormap-reset-range"


class ColorMapLabel(str, Enum):
    WRAPPER = "Surface coloring"
    SELECT = "Colormap"
    RANGE = "Value range"
    RESET_RANGE = "Reset range"


class ColorMapKeepOptions(str, Enum):
    KEEP = "Keep range"


def surface_settings_view(get_uuid: Callable) -> wcc.Selectors:
    return wcc.Selectors(
        label=ColorMapLabel.WRAPPER,
        children=[
            wcc.Dropdown(
                label=ColorMapLabel.SELECT,
                id=get_uuid(ColorMapID.SELECT),
                options=[
                    {"label": name, "value": name} for name in ["viridis_r", "seismic"]
                ],
                value="viridis_r",
                clearable=False,
            ),
            wcc.RangeSlider(
                label=ColorMapLabel.RANGE,
                id=get_uuid(ColorMapID.RANGE),
                updatemode="drag",
                tooltip={
                    "always_visible": True,
                    "placement": "bottomLeft",
                },
            ),
            wcc.Checklist(
                id=get_uuid(ColorMapID.KEEP_RANGE),
                options=[
                    {
                        "label": opt,
                        "value": opt,
                    }
                    for opt in ColorMapKeepOptions
                ],
            ),
            html.Button(
                children=ColorMapLabel.RESET_RANGE,
                style={"marginTop": "5px"},
                id=get_uuid(ColorMapID.RESET_RANGE),
            ),
        ],
    )
