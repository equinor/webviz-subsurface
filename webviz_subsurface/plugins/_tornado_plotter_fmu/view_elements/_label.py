from dash import html
from dash.development.base_component import Component
from webviz_config.webviz_assets import WEBVIZ_ASSETS
from webviz_config.webviz_plugin_subclasses import ViewElementABC


class Label(ViewElementABC):
    """View element for displaying the label at det top"""

    class IDs:
        # pylint: disable=too-few-public-methods
        LABEL = "label"

    def __init__(self) -> None:
        super().__init__()

    def inner_layout(self) -> Component:
        return html.Label(
            children="Tornado Plotter",
            id=self.register_component_unique_id(Label.IDs.LABEL),
            style={"textAlign": "center", "font-weight": "bold", "font-size": 20},
        )
