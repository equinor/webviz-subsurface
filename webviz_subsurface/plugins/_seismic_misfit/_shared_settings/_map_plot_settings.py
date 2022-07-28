from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class MapPlotSettings(SettingsGroupABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        COLOR_BY = "color-by"
        COLOR_RANGE_SCALING = "color-range-scaling"
        MARKER_SIZE = "marker-size"
        POLYGONS = "polygons"

    def __init__(self, map_intial_marker_size: int, polygon_names: List) -> None:
        super().__init__("Map plot settings")
        self.map_intial_marker_size = map_intial_marker_size
        self.polygon_names = polygon_names

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Color by",
                id=self.register_component_unique_id(self.Ids.COLOR_BY),
                options=[
                    {
                        "label": "region",
                        "value": "region",
                    },
                    {
                        "label": "obs",
                        "value": "obs",
                    },
                    {
                        "label": "obs error",
                        "value": "obs_error",
                    },
                ],
                value="obs",
                clearable=False,
                persistence=True,
                persistence_type="memory",
            ),
            wcc.Dropdown(
                label="Color range scaling (relative to max)",
                id=self.register_component_unique_id(self.Ids.COLOR_RANGE_SCALING),
                options=[
                    {"label": f"{x:.0%}", "value": x}
                    for x in [
                        0.1,
                        0.2,
                        0.3,
                        0.4,
                        0.5,
                        0.6,
                        0.7,
                        0.8,
                        0.9,
                        1.0,
                    ]
                ],
                style={"display": "block"},
                value=0.8,
                clearable=False,
                persistence=True,
                persistence_type="memory",
            ),
            wcc.Dropdown(
                label="Marker size",
                id=self.register_component_unique_id(self.Ids.MARKER_SIZE),
                options=[
                    {"label": val, "value": val}
                    for val in sorted(
                        [
                            self.map_intial_marker_size,
                            2,
                            5,
                            8,
                            10,
                            12,
                            14,
                            16,
                            18,
                            20,
                            25,
                            30,
                        ]
                    )
                ],
                value=self.map_intial_marker_size,
                clearable=False,
                persistence=True,
                persistence_type="memory",
            ),
            wcc.Dropdown(
                label="Polygons",
                id=self.register_component_unique_id(self.Ids.POLYGONS),
                optionHeight=60,
                options=[
                    {"label": polyname, "value": polyname}
                    for polyname in self.polygon_names
                ],
                multi=False,
                clearable=True,
                persistence=True,
                persistence_type="memory",
            ),
        ]
