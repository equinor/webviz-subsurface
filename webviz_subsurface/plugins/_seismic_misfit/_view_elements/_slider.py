from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import ViewElementABC


class SeismicSlider(ViewElementABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        SLIDER = "slider"

    def __init__(self, map_y_range: List[float]) -> None:
        super().__init__()
        self.map_y_range = map_y_range

    def inner_layout(self) -> Component:
        return wcc.Slider(
            id=self.register_component_unique_id(self.Ids.SLIDER),
            min=self.map_y_range[0],
            max=self.map_y_range[1],
            value=(self.map_y_range[0] + self.map_y_range[1]) / 2,
            step=100,
            marks={
                str(self.map_y_range[0]): f"min={round(self.map_y_range[0]):,}",
                str(self.map_y_range[1]): f"max={round(self.map_y_range[1]):,}",
            },
        )
