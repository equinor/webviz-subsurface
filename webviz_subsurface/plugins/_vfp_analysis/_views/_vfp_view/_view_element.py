from dash import html
from webviz_config.webviz_plugin_subclasses import ViewElementABC


class VfpViewElement(ViewElementABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        CHART = "chart"

    def __init__(self) -> None:
        super().__init__()

    def inner_layout(self) -> html.Div:
        return html.Div("Something")
