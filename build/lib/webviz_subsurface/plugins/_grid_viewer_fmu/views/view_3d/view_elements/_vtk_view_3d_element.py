from dash import dcc, html
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import ViewElementABC
from webviz_subsurface_components import DeckGLMap


class VTKView3D(ViewElementABC):
    class Ids(StrEnum):
        ID = "vtk"
        VIEW = "vtk-view"

        INFOBOX = "info-box"
        ACTUALVALUERANGE = "actual-value-range"

    def __init__(self) -> None:
        super().__init__()

    def inner_layout(self) -> Component:

        return html.Div(
            style={"position": "relative", "height": "90vh"},
            children=[
                html.Div(
                    style={"zIndex": 10000, "position": "absolute", "top": 0},
                    children=[
                        html.Div(
                            children=[
                                html.Div(
                                    id=self.register_component_unique_id(
                                        VTKView3D.Ids.INFOBOX
                                    ),
                                    style={
                                        "border": "black",
                                        "margin": "10px",
                                        "padding": "5px",
                                        "fontSize": "0.8em",
                                        "borderRadius": "10px",
                                        "backgroundColor": "lightgrey",
                                    },
                                ),
                            ]
                        ),
                    ],
                ),
                html.Div(
                    style={"position": "absolute", "width": "100%", "height": "90%"},
                    children=[
                        DeckGLMap(
                            id=self.register_component_unique_id(VTKView3D.Ids.VIEW),
                            layers=[
                                {
                                    "@@type": "AxesLayer",
                                    "id": "axes-layer",
                                    "bounds": [
                                        0,
                                        0,
                                        -1,
                                        1,
                                        1,
                                        0,
                                    ],
                                },
                                {
                                    "@@type": "Grid3DLayer",
                                    "id": "Grid3DLayer",
                                    "material": True,
                                    "colorMapName": "Physics reverse",
                                    "scaleZ": 1,
                                    "pointsUrl": "/grid/points/test",
                                    "polysUrl": "/grid/polys/test",
                                    "propertiesUrl": "/grid/scalar/test",
                                },
                            ],
                            views={
                                "layout": [1, 1],
                                "viewports": [{"id": "view_1", "show3D": True}],
                            },
                        ),
                    ],
                ),
                html.Div(
                    style={"position": "absolute", "bottom": 0},
                    children=html.Label(
                        children="⚠️ This is an experimental plugin that might be removed "
                        "on short notice. Verify all results in ResInsight or RMS.",
                    ),
                ),
                dcc.Store(
                    id=self.register_component_unique_id(
                        VTKView3D.Ids.ACTUALVALUERANGE
                    ),
                    data=[0, 0],
                ),
            ],
        )
