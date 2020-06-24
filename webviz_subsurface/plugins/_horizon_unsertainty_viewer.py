from uuid import uuid4
from pathlib import Path
from typing import List

import dash_html_components as html
import dash_core_components as dcc

from webviz_config import WebvizPluginABC


class HorizonUnsertaintyViewer(WebvizPluginABC):

    def __init__(
        self,
        app,
        surfacefiles: List[Path],
        surfacenames: list = None,
    ):

    super().__init__()
    self.set_callbacks(app)
    self.plotly_theme = app.webviz_settings["theme"].plotly_theme
    self.uid = uuid4()
    self.surfacefiles = [str(surfacefile) for surfacefile in surfacefiles]
    if surfacenames is not None:
            if len(surfacenames) != len(surfacefiles):
                raise ValueError(
                    "List of surface names specified should be same length as list of surfacefiles"
                )
            self.surfacenames = surfacenames
        else:
            self.surfacenames = [Path(surfacefile).stem for surfacefile in surfacefiles]

    def ids(self, element):
        """Generate unique id for dom element"""
        return f"{element}-id-{self.uid}"


    '''
    Dette trenger vi ikke foreløpig.
    @property
    def tour_steps(self):
        return [
            {
                "id": self.ids("layout"),
                "content": (
                    "This is a plugin to display surfaces and cross-sections from a seismic cube."
                ),
            },
            {"id": self.ids("surface"), "content": ("Choose which surface you want to display."),},
            {
                "id": self.ids("map-view"),
                "content": (
                    "Map view of the surface. Use the right toolbar to "
                    "draw a random line."
                ),
            },
            {
                "id": self.ids("fence-view"),
                "content": (
                    "Cross section view of the seismic cube along the edited line. "
                    "The view is empty until a line is drawn in the map view."
                ),
            },
            {
                "id": self.ids("surface-type"),
                "content": (
                    "Display the z-value of the surface (e.g. depth) or "
                    "the seismic value where the surface intersect the seismic cube."
                ),
            },
            {"id": self.ids("cube"), "content": "The visualized cube.",},
            {
                "id": self.ids("color-scale"),
                "content": ("Click this button to change colorscale"),
            },
            {
                "id": self.ids("color-values"),
                "content": ("Drag either node of slider to truncate color ranges"),
            },
            {
                "id": self.ids("color-range-btn"),
                "content": (
                    "Click this button to update color slider min/max and reset ranges."
                ),
            },
        ]
    '''

    @property
    def map_layout(self):
        """Layout for Map Viewer"""

    @property
    def fence_layout(self):
        """Layout for the Cross Section Viewer"""
        return html.Div(
            children=[
                '''
                wcc.FlexBox(
                    children=[
                        # Her må vi finne ut hvordan dropdown alternativ vi vil ha.
                        html.Div(
                            children=[
                                html.Label(
                                    style={
                                        "font-weight": "bold",
                                        "textAlign": "center",
                                    },
                                    children="Select Seismic Cube",
                                ),
                                dcc.Dropdown(
                                    id=self.ids("cube"),
                                    options=[
                                        {"label": Path(cube).stem, "value": cube}
                                        for cube in self.segyfiles
                                    ],
                                    value=self.segyfiles[0],
                                    clearable=False,
                                ),
                            ]
                        ),
                        # Her må vi finne ut om vi vil har colorscale alternativer.
                        html.Div(
                            style={"zIndex": 2000},
                            children=[
                                html.Label(
                                    style={
                                        "font-weight": "bold",
                                        "textAlign": "center",
                                    },
                                    children="Set colorscale",
                                ),
                                wcc.ColorScales(
                                    id=self.ids("color-scale"),
                                    colorscale=self.initial_colors,
                                    nSwatches=12,
                                ),
                            ],
                        ),
                    ],
                ),
                # Treng vi en slider for color range??
                wcc.FlexBox(
                    children=[
                        html.Div(
                            style={
                                "marginRight": "50px",
                                "marginTop": "20px",
                                "marginBottom": "0px",
                                "flex": 1,
                            },
                            children=[
                                html.Label(
                                    style={
                                        "font-weight": "bold",
                                        "textAlign": "center",
                                    },
                                    children="Set color range",
                                ),
                                dcc.RangeSlider(
                                    id=self.ids("color-values"),
                                    tooltip={"always_visible": True},
                                ),
                            ],
                        ),
                        html.Div(
                            style={"flex": 1},
                            children=html.Button(
                                id=self.ids("color-range-btn"), children="Reset Range"
                            ),
                        ),
                    ],
                ),
                '''
                html.Div(
                    style={"height": "800px"},
                    children=wcc.Graph(
                        config={"displayModeBar": False}, id=self.ids("fence-view") # Sett inn figur her
                    ),
                ),
            ],
        )

            
    @property
    def layout(self):
            return wcc.FlexBox(
                # id=self.ids("layout"),
                children=[
                    # Har kommentert ut map_layout intil videre
                    # html.Div(style={"flex": 1}, children=self.map_layout),
                    html.Div(style={"flex": 1}, children=self.fence_layout),
                ],
            )


