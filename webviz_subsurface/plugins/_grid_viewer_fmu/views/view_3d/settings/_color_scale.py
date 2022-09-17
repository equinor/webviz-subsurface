from typing import List

import webviz_core_components as wcc
from dash import dcc, html
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


def list_to_options(values: List) -> List:
    return [{"value": val, "label": val} for val in values]


class ColorScale(SettingsGroupABC):
    class Ids(StrEnum):
        COLORMAP = "colormap"
        COLORRANGEMANUAL = "color-range-lock"
        COLORMIN = "color-min"
        COLORMAX = "color-max"

    def __init__(self) -> None:
        super().__init__("Color scale")
        self.colormaps = ["erdc_rainbow_dark", "Viridis (matplotlib)", "BuRd"]

    def layout(self) -> List[Component]:

        return [
            html.Div(
                children=[
                    wcc.Label("Color map"),
                    wcc.Dropdown(
                        id=self.register_component_unique_id(ColorScale.Ids.COLORMAP),
                        options=list_to_options(self.colormaps),
                        value=self.colormaps[0],
                        clearable=False,
                    ),
                    html.Div(
                        children=[
                            wcc.Checklist(
                                id=self.register_component_unique_id(
                                    ColorScale.Ids.COLORRANGEMANUAL
                                ),
                                options=[
                                    {
                                        "label": "Manual color range",
                                        "value": "manual_color",
                                    }
                                ],
                                value=[],
                                style={"marginTop": "10px"},
                                persistence=None,
                            ),
                            html.Div(
                                style={"display": "flex"},
                                children=[
                                    wcc.Label(
                                        style={"marginRight": "10px"}, children="Min: "
                                    ),
                                    dcc.Input(
                                        style={"maxWidth": "80px"},
                                        id=self.register_component_unique_id(
                                            ColorScale.Ids.COLORMIN
                                        ),
                                        type="number",
                                        minLength=1,
                                        disabled=True,
                                        placeholder="From data",
                                    ),
                                    wcc.Label(
                                        style={
                                            "marginLeft": "10px",
                                            "marginRight": "10px",
                                        },
                                        children="Max: ",
                                    ),
                                    dcc.Input(
                                        style={"maxWidth": "80px"},
                                        id=self.register_component_unique_id(
                                            ColorScale.Ids.COLORMAX
                                        ),
                                        type="number",
                                        minLength=1,
                                        disabled=True,
                                        placeholder="From data",
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ]
