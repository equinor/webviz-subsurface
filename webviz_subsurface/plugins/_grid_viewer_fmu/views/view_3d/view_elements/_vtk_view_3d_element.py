import webviz_core_components as wcc
import webviz_vtk
from dash import dcc, html
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import ViewElementABC


class VTKView3D(ViewElementABC):
    class Ids(StrEnum):
        ID = "vtk"
        VIEW = "vtk-view"
        GRID_REPRESENTATION = "grid-representation"
        GRID_POLYDATA = "grid-polydata"
        GRID_CELLDATA = "grid-celldata"
        PICK_REPRESENTATION = "pick-representation"
        PICK_SPHERE = "pick-sphere"
        CAMERASET = "camera-set"
        RESETCAMERA = "reset-camera"
        INFOBOX = "info-box"
        ACTUALVALUERANGE = "actual-value-range"
        CLICKED_DATA = "clicked-data"
        INTERACTION_DIALOG_BUTTON = "interaction-dialog-button"
        INTERACTION_DIALOG = "interaction-dialog"
        INTERACTION_DIALOG_READOUT = "interaction-dialog-readout"
        INTERACTION_CHECKLIST = "interaction-checklist"

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
                                    [
                                        html.Button(
                                            style={
                                                "backgroundColor": "white",
                                                "color": "black",
                                                "margin": "10px",
                                            },
                                            id=self.register_component_unique_id(
                                                VTKView3D.Ids.RESETCAMERA
                                            ),
                                            children="Reset camera",
                                        ),
                                    ]
                                ),
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
                                html.Div(
                                    id=self.register_component_unique_id(
                                        VTKView3D.Ids.CLICKED_DATA
                                    ),
                                    style={
                                        "border": "black",
                                        "margin": "10px",
                                        "padding": "5px",
                                        "fontSize": "0.8em",
                                        "borderRadius": "10px",
                                        "backgroundColor": "lightgrey",
                                    },
                                    children=[],
                                ),
                            ]
                        ),
                    ],
                ),
                html.Div(
                    style={
                        "zIndex": 10000,
                        "position": "absolute",
                        "top": 0,
                        "right": 0,
                    },
                    children=[
                        html.Button(
                            style={
                                "backgroundColor": "white",
                                "color": "black",
                                "margin": "10px",
                            },
                            id=self.register_component_unique_id(
                                VTKView3D.Ids.INTERACTION_DIALOG_BUTTON
                            ),
                            children="Mouse settings",
                        )
                    ],
                ),
                html.Div(
                    style={"position": "absolute", "width": "100%", "height": "100%"},
                    children=[
                        webviz_vtk.View(
                            id=self.register_component_unique_id(VTKView3D.Ids.VIEW),
                            # background=[255, 245, 196],
                            style={"height": "90vh"},
                            pickingModes=["click"],
                            autoResetCamera=True,
                            children=[
                                webviz_vtk.GeometryRepresentation(
                                    id=self.register_component_unique_id(
                                        VTKView3D.Ids.GRID_REPRESENTATION
                                    ),
                                    showCubeAxes=True,
                                    showScalarBar=True,
                                    # scalarBarStyle={
                                    #     "axisTextStyle": {"fontColor": "black"},
                                    #     "tickTextStyle": {"fontColor": "black"},
                                    # },
                                    # cubeAxesStyle={
                                    #     "gridLines": False,
                                    #     "strokeColor": "black",
                                    #     "strokeStyle": "black",
                                    #     "fontColor": "black",
                                    #     "axisTextStyle": {
                                    #         "fontColor": "black",
                                    #         "strokeColor": "black",
                                    #     },
                                    #     "tickTextStyle": {
                                    #         "fontColor": "black",
                                    #         "strokeColor": "black",
                                    #     },
                                    # },
                                    children=[
                                        webviz_vtk.PolyData(
                                            id=self.register_component_unique_id(
                                                VTKView3D.Ids.GRID_POLYDATA
                                            ),
                                            children=[
                                                webviz_vtk.CellData(
                                                    [
                                                        webviz_vtk.DataArray(
                                                            id=self.register_component_unique_id(
                                                                VTKView3D.Ids.GRID_CELLDATA
                                                            ),
                                                            registration="setScalars",
                                                            name="scalar",
                                                        )
                                                    ]
                                                )
                                            ],
                                        )
                                    ],
                                    property={"edgeVisibility": True},
                                ),
                                webviz_vtk.GeometryRepresentation(
                                    id=self.register_component_unique_id(
                                        VTKView3D.Ids.PICK_REPRESENTATION
                                    ),
                                    actor={"visibility": False},
                                    children=[
                                        webviz_vtk.Algorithm(
                                            id=self.register_component_unique_id(
                                                VTKView3D.Ids.PICK_SPHERE
                                            ),
                                            vtkClass="vtkSphereSource",
                                        )
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    style={"position": "absolute", "bottom": 0},
                    children=html.Label(
                        style={
                            "color": "white",
                        },
                        children="⚠️ This is an experimental plugin that might be removed "
                        "on short notice. Verify all results in ResInsight or RMS.",
                    ),
                ),
                dcc.Store(
                    id=self.register_component_unique_id(VTKView3D.Ids.CAMERASET),
                    data=False,
                ),
                dcc.Store(
                    id=self.register_component_unique_id(
                        VTKView3D.Ids.ACTUALVALUERANGE
                    ),
                    data=[0, 0],
                ),
                wcc.Dialog(
                    id=self.register_component_unique_id(
                        VTKView3D.Ids.INTERACTION_DIALOG
                    ),
                    title="",
                    open=False,
                    children=[
                        wcc.RadioItems(
                            id=self.register_component_unique_id(
                                VTKView3D.Ids.INTERACTION_CHECKLIST
                            ),
                            vertical=False,
                            options=[
                                {
                                    "label": "ResInsight/RMS",
                                    "value": "resinsight_rms",
                                },
                                {"label": "VTK", "value": "vtk"},
                            ],
                            value="resinsight_rms",
                        ),
                        html.Br(),
                        html.Div(
                            id=self.register_component_unique_id(
                                VTKView3D.Ids.INTERACTION_DIALOG_READOUT
                            )
                        ),
                    ],
                ),
            ],
        )
