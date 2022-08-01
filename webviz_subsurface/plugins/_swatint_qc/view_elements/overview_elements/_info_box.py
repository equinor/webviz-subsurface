import webviz_core_components as wcc
from dash import html
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import ViewElementABC

from .._layout_style import LayoutStyle


class InfoBox(ViewElementABC):
    class IDs:
        # pylint disable=too-few-public-methods
        FRAME = "frame"
        KEY_NUMBERS = "key-numbers"

    def __init__(self, datamodel, informaiton_dialog) -> None:
        super().__init__()
        max_pc, min_pc = datamodel.pc_scaling_min_max
        wvol, hcvol = datamodel.vol_diff_total
        self.information_dialog = informaiton_dialog
        self.number_style = {
            "font-weight": "bold",
            "font-size": "17px",
            "margin-left": "20px",
        }
        self.data = [
            ("HC Volume difference:", f"{hcvol:.2f} %"),
            ("Water Volume difference:", f"{wvol:.2f} %"),
            ("Maximum Capillary Pressure scaling:", f"{max_pc:.1f}"),
            ("Minimum Capillary Pressure scaling:", f"{min_pc:.3g}"),
        ]

    def inner_layout(self) -> Component:
        return wcc.Frame(
            style={"height": "90%"},
            id=self.register_component_unique_id(InfoBox.IDs.FRAME),
            children=[
                wcc.Header("Information", style=LayoutStyle.HEADER),
                self.information_dialog,
                wcc.Header("Key numbers", style=LayoutStyle.HEADER),
                html.Div(
                    [
                        html.Div([text, html.Span(num, style=self.number_style)])
                        for text, num in self.data
                    ],
                    id=self.register_component_unique_id(InfoBox.IDs.KEY_NUMBERS),
                ),
            ],
        )
