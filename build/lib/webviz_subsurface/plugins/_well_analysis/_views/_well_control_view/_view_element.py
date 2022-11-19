from dash import html
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import ViewElementABC


class WellControlViewElement(ViewElementABC):
    class Ids(StrEnum):
        CHART = "chart"

    def __init__(self) -> None:
        super().__init__()

    def inner_layout(self) -> html.Div:
        return html.Div(
            id=self.register_component_unique_id(WellControlViewElement.Ids.CHART)
        )
