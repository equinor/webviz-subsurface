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


class ColorLinkID(str, Enum):
    COLORMAP = "colormap"
    RANGE = "range"


def settings_view(get_uuid: Callable) -> html.Div:
    return make_link_checkboxes(get_uuid) + [
        surface_settings_view(get_uuid, view="view1"),
        surface_settings_view(get_uuid, view="view2"),
    ]


def make_link_checkboxes(get_uuid):
    return [
        wcc.Checklist(
            id=get_uuid(link_id),
            options=[{"label": f"Link {link_id}", "value": link_id}],
        )
        for link_id in ColorLinkID
    ]


def surface_settings_view(get_uuid: Callable, view: str) -> wcc.Selectors:
    return wcc.Selectors(
        label=f"{ColorMapLabel.WRAPPER} ({view})",
        children=[
            wcc.Dropdown(
                label=ColorMapLabel.SELECT,
                id={"view": view, "id": get_uuid(ColorMapID.SELECT)},
                options=[
                    {"label": name, "value": name} for name in ["viridis_r", "seismic"]
                ],
                value="viridis_r",
                clearable=False,
            ),
            wcc.RangeSlider(
                label=ColorMapLabel.RANGE,
                id={"view": view, "id": get_uuid(ColorMapID.RANGE)},
                updatemode="drag",
                tooltip={
                    "always_visible": True,
                    "placement": "bottomLeft",
                },
            ),
            wcc.Checklist(
                id={"view": view, "id": get_uuid(ColorMapID.KEEP_RANGE)},
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
                id={"view": view, "id": get_uuid(ColorMapID.RESET_RANGE)},
            ),
        ],
    )
