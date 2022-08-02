import plotly.graph_objects as go
import webviz_core_components as wcc
from dash import dcc, html
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import ViewElementABC

from .._swatint import SwatinitQcDataModel
from ._fullscreen import FullScreen
from ._layout_style import LayoutStyle


class WaterViewelement(ViewElementABC):
    """All elements visible in the 'Water Initialization QC plots'-tab
    gathered in one viewelement"""

    class IDs:
        # pylint: disable=too-few-public-methods
        MAIN_FIGURE = "main-figure"
        MAP_FIGURE = "map-figure"

    def __init__(
        self,
        datamodel: SwatinitQcDataModel,
        main_figure: go.Figure,
        map_figure: go.Figure,
        qc_volumes: dict,
    ) -> None:
        super().__init__()
        self.datamodel = datamodel
        self.main_figure = main_figure
        self.map_figure = map_figure
        self.qc_volumes = qc_volumes

    def inner_layout(self) -> wcc.FlexBox:
        return wcc.FlexBox(
            children=[
                wcc.FlexColumn(
                    flex=4,
                    children=wcc.Graph(
                        style={"height": "85vh"},
                        id=self.register_component_unique_id(
                            WaterViewelement.IDs.MAIN_FIGURE
                        ),
                        figure=self.main_figure,
                    ),
                ),
                wcc.FlexColumn(
                    flex=1,
                    children=[
                        FullScreen(
                            wcc.Graph(
                                responsive=True,
                                style={"height": "100%", "min-height": "45vh"},
                                id=self.register_component_unique_id(
                                    WaterViewelement.IDs.MAP_FIGURE
                                ),
                                figure=self.map_figure,
                            )
                        ),
                        self.info_box(self.qc_volumes, height="35vh"),
                    ],
                ),
            ]
        )

    @staticmethod
    def info_box(qc_vols: dict, height: str) -> html.Div:
        return html.Div(
            [
                wcc.Header("Information about selection", style=LayoutStyle.HEADER),
                html.Div(
                    "EQLNUMS:", style={"font-weight": "bold", "font-size": "15px"}
                ),
                html.Div(", ".join([str(x) for x in qc_vols["EQLNUMS"]])),
                html.Div(
                    "SATNUMS:", style={"font-weight": "bold", "font-size": "15px"}
                ),
                html.Div(", ".join([str(x) for x in qc_vols["SATNUMS"]])),
                html.Div(
                    html.Span("Reservoir Volume Difference:"),
                    style={"font-weight": "bold", "margin-top": "10px"},
                ),
                html.Div(
                    children=[
                        html.Div(line)
                        for line in [
                            f"Water Volume Diff: {qc_vols['WVOL_DIFF']/(10**6):.2f} Mrm3",
                            f"Water Volume Diff (%): {qc_vols['WVOL_DIFF_PERCENT']:.2f}",
                            f"HC Volume Diff (%): {qc_vols['HCVOL_DIFF_PERCENT']:.2f}",
                        ]
                    ],
                ),
            ],
            style={"height": height, "padding": "10px"},
        )
