from typing import List

import webviz_core_components as wcc
from dash import dcc, html
from dash.development.base_component import Component
from webviz_config import WebvizConfigTheme
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ...._types import LinePlotOptions
from .._utils import color_figure


class ParamRespVizualisation(SettingsGroupABC):
    class Ids(StrEnum):
        LINE_OPTION = "line-option"
        CHECKBOX_OPTIONS = "checkbox-options"
        CHECKBOX_OPTIONS_STORE = "checkbox-options-store"
        COLOR_SELECTOR = "color-selector"
        OPACITY_SELECTOR = "opacity-selector"

    def __init__(self, theme: WebvizConfigTheme) -> None:
        super().__init__("Vizualisation")
        self._theme_colors = theme.plotly_theme.get("layout", {}).get("colorway", [])

    def layout(self) -> List[Component]:
        return [
            wcc.RadioItems(
                id=self.register_component_unique_id(self.Ids.LINE_OPTION),
                options=[
                    {
                        "label": "Individual realizations",
                        "value": LinePlotOptions.REALIZATIONS,
                    },
                    {
                        "label": "Statistical lines",
                        "value": LinePlotOptions.STATISTICS,
                    },
                    {
                        "label": "Statistics + Realizations",
                        "value": LinePlotOptions.STATISTICS_AND_REALIZATIONS,
                    },
                ],
                value=LinePlotOptions.REALIZATIONS,
            ),
            wcc.Checklist(
                id=self.register_component_unique_id(self.Ids.CHECKBOX_OPTIONS),
                options=[
                    {"label": "Dateline", "value": "DateLine"},
                    {"label": "Observations", "value": "Observations"},
                ],
                value=["DateLine", "Observations"],
            ),
            dcc.Store(
                id=self.register_component_unique_id(self.Ids.CHECKBOX_OPTIONS_STORE),
                storage_type="session",
            ),
            html.Div(
                style={"margin-top": "5px"},
                children=[
                    wcc.Label("Colors"),
                    wcc.Graph(
                        style={"height": 50},
                        id=self.register_component_unique_id(self.Ids.COLOR_SELECTOR),
                        config={"displayModeBar": False},
                        figure=color_figure(
                            colors=[self._theme_colors, "Greys", "BrBG"],
                            bargap=0.2,
                            height=50,
                        ),
                    ),
                ],
            ),
            html.Div(
                style={"margin-top": "5px"},
                children=[
                    "Opacity:",
                    dcc.Input(
                        id=self.register_component_unique_id(self.Ids.OPACITY_SELECTOR),
                        type="number",
                        min=0,
                        max=1,
                        step=0.1,
                        value=0.5,
                        style={"margin-left": "10px"},
                    ),
                ],
            ),
        ]
