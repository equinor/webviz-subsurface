from typing import List, Tuple, Dict, Optional

from dash.development.base_component import Component
from dash import Input, Output, State, callback, no_update
import webviz_core_components as wcc
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC
from webviz_subsurface._providers.ensemble_grid_provider import EnsembleGridProvider

from webviz_subsurface.plugins._grid_viewer._types import PROPERTYTYPE
from webviz_subsurface.plugins._grid_viewer._layout_elements import ElementIds


def list_to_options(values: List) -> List:
    return [{"value": val, "label": val} for val in values]


class Settings(SettingsGroupABC):
    def __init__(self) -> None:
        super().__init__("Settings")
        self.colormaps = ["erdc_rainbow_dark", "Viridis (matplotlib)", "BuRd"]

    def layout(self) -> List[Component]:

        return [
            wcc.Slider(
                label="Z Scale",
                id=self.register_component_uuid(ElementIds.Settings.ZSCALE),
                min=1,
                max=10,
                value=1,
                step=1,
            ),
            wcc.Selectors(
                label="Color map",
                children=[
                    wcc.Dropdown(
                        id=self.register_component_uuid(ElementIds.Settings.COLORMAP),
                        options=list_to_options(self.colormaps),
                        value=self.colormaps[0],
                        clearable=False,
                    )
                ],
            ),
            wcc.Checklist(
                id=self.register_component_uuid(ElementIds.Settings.SHOW_CUBEAXES),
                options=["Show bounding box"],
                value=["Show bounding box"],
            ),
        ]
