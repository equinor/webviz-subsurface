from uuid import uuid4
from pathlib import Path
from typing import List
import dash
import dash_table
import pandas as pd
import numpy as np
import numpy.ma as ma
import plotly.graph_objects as go
from matplotlib.colors import ListedColormap
import xtgeo
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import webviz_core_components as wcc
from webviz_subsurface_components import LayeredMap
from webviz_config import WebvizPluginABC
from webviz_config.webviz_store import webvizstore
from webviz_config.utils import calculate_slider_step

from .._datainput.well import load_well
from .._datainput.surface import make_surface_layer, get_surface_fence, load_surface
from .._datainput.huv_xsection import HuvXsection


class HorizonUncertaintyViewer(WebvizPluginABC):
    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
    app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
    #app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    """
This plugin visualizes surfaces in a map view and seismic in a cross section view.
The cross section is defined by a polyline interactively edited in the map view.
* `surfacefiles`: List of file paths to Irap Binary surfaces
* `surfacenames`: Corresponding list of displayed surface names
* `zunit`: z-unit for display
* `colors`: List of colors to use
"""

    ### Initialize ###
    def __init__(
        self,
        app,
        surfacefiles: List[Path],
        surfacefiles_de: List[Path],
        wellfiles: List[Path],
        zonation_data: List[Path],
        conditional_data: List[Path],
        target_points: List[Path] = None,
        well_points: List[Path] = None,
        surfacenames: list = None,
        wellnames: list = None,
        zonelog: str = None,
        zunit="depth (m)",
        zonemin: int = 1,
    ):

        super().__init__()
        self.zunit = zunit
        self.surfacefiles = [str(surffile) for surffile in surfacefiles]
        self.surfacefiles_de = [str(surfacefile_de) for surfacefile_de in surfacefiles_de]
        self.surface_attributes = {x: {} for x in surfacefiles}
        self.target_points = [Path(target_point) for target_point in target_points]
        self.well_points = well_points
        for i, surfacefile in enumerate(surfacefiles):
            self.surface_attributes[surfacefile] = {"color": get_color(i), "error_path": surfacefiles_de[i]}

        if surfacenames is not None:
            if len(surfacenames) != len(surfacefiles):
                raise ValueError(
                    "List of surface names specified should be same length as list of surfacefiles"
                )
            self.surfacenames = surfacenames
        else:
            self.surfacenames = [Path(surfacefile).stem for surfacefile in surfacefiles]

        self.wellfiles = [str(wellfile) for wellfile in wellfiles]
        if wellnames is not None:
            if len(wellnames) != len(wellfiles):
                raise ValueError(
                    "List of surface names specified should be same length as list of surfacefiles"
                )
            self.wellnames = wellnames
        else:
            self.wellnames = [Path(wellfile).stem for wellfile in wellfiles]
        self.zonation_data= [Path(zond_data) for zond_data in zonation_data]
        self.conditional_data= [Path(cond_data) for cond_data in conditional_data]
        self.zonemin = zonemin
        self.zonelog = zonelog       
        self.plotly_theme = app.webviz_settings["theme"].plotly_theme
        self.uid = uuid4()
        self.set_callbacks(app)
        self.xsec = HuvXsection(self.surface_attributes,self.zonation_data,self.conditional_data)
        self.xsec.create_well(wellfiles[0],self.surfacefiles)


    ### Generate unique ID's ###
    def ids(self, element):
        return f"{element}-id-{self.uid}"

    ### Layout map section ###
    @property
    def map_layout(self):
        return html.Div(
                    children=[
                        wcc.FlexBox(
                            children=[
                                html.Div(
                                    children=[
                                        html.Label(
                                            style={
                                                "font-weight": "bold",
                                                "textAlign": "center",
                                            },
                                            children="Select surface",
                                        ),
                                        dcc.Dropdown(
                                            id=self.ids("map-dropdown"),
                                            options=[
                                                {"label": name, "value": path}
                                                for name, path in zip(
                                                    self.surfacenames, self.surfacefiles_de
                                                )
                                            ],
                                            value=self.surfacefiles_de[0],
                                            clearable=False,
                                        ),
                                    ]
                                ),
                            ],
                        ),
                        html.Div(
                            style={
                                "marginTop": "20px",
                                "height": "800px",
                                "zIndex": -9999,
                            },
                            children=LayeredMap(
                                id=self.ids("map-view"),
                                draw_toolbar_polyline=True,
                                hillShading=True,
                                layers=[],
                            ),
                        )   
                    ]
                ),

    ### Layout cross section ###
    @property
    def cross_section_layout(self):
        return html.Div(
            children=[
                wcc.FlexBox(
                    children=[
                        html.Div(
                            children=[
                                html.Label(
                                    style={
                                        "font-weight": "bold",
                                        "textAlign": "center",
                                    },
                                    children="Select well",
                                ),
                                dcc.Dropdown(
                                    id=self.ids("well-dropdown"),
                                    options=[
                                        {"label": name, "value": path}
                                        for name, path in zip(
                                            self.wellnames, self.wellfiles
                                        )
                                    ],
                                    value=self.wellfiles[0],
                                    clearable=False,
                                ),
                            ]
                        ),
                    ],
                ),
                html.Div(
                    children=[
                        dbc.Button("Graph Settings", id=self.ids("button-open-graph-settings")),
                        dbc.Modal(
                            children=[
                                dbc.ModalHeader("Graph Settings"),
                                dbc.ModalBody(
                                    children=[
                                        html.Label(
                                            style={
                                                "font-weight": "bold",
                                                "textAlign": "Left",
                                            },
                                            children="Select Surfaces",
                                        ),
                                        dcc.Checklist(
                                            id=self.ids('all-surfaces-checkbox'),
                                            options=[{'label': 'all', 'value': 'True'}],
                                            value=['True'],
                                        ),
                                        dcc.Checklist(
                                            id=self.ids('surfaces-checklist'),
                                            options=[
                                                {"label": name, "value": path}
                                                for name, path in zip(
                                                    self.surfacenames, self.surfacefiles
                                                )
                                            ],
                                            value=self.surfacefiles,
                                        ),
                                        dcc.Checklist(
                                            id=self.ids('surfaces_de_checklist'),
                                            options=[
                                                {"label": name+'_error', "value": path}
                                                for name, path in zip(
                                                    self.surfacenames, self.surfacefiles_de
                                        )
                                    ],
                                    value=self.surfacefiles_de,
                                ),
                                    ],
                                ),
                                dbc.ModalFooter(
                                    dbc.Button("Close", id=self.ids("button-close-graph-settings"), className="ml-auto")
                                ),
                            ],
                            id=self.ids("modal-graph-settings"),
                            size="sm",
                            centered=True,
                            backdrop=False,
                            fade=False,
                        ),
                    ],
                ),
                html.Div(
                    children=[
                        html.Div(
                            style={
                                "marginTop": "0px",
                                "height": "800px",
                                "zIndex": -9999,
                            },
                            children=wcc.Graph(
                                figure={"displayModeBar": True}, id=self.ids("cross-section-view")
                            ),
                        )
                    ]
                ),
            ]
        )

    @property
    def table_layout(self):
        df = pd.read_csv(self.target_points[0])
        return dash_table.DataTable(
            id='table',
            columns=[{"name": i, "id": i} for i in df.columns],
            data=df.to_dict('records'),
        )

    ### Flexbox ###
    @property
    def layout(self):
        return dcc.Tabs(children=[
            dcc.Tab(
                label="Cross section & map view",
                children=[
                    wcc.FlexBox(
                        id=self.ids("layout"),
                        children=[
                            html.Div(style={"flex": 1}, children=self.map_layout),
                            html.Div(style={"flex": 1}, children=self.cross_section_layout),
                        ]
                    )
                ]
            ),
            dcc.Tab(
                label="Table view",
                children=[html.Div(children=self.table_layout)]
            )
        ])

    ### Callbacks map view and cross-section-view ###
    def set_callbacks(self, app):
        @app.callback(
            Output(self.ids("map-view"), "layers"),
            [
                Input(self.ids("map-dropdown"), "value"),
            ],
        )
        def render_map(surfacepath):
            surface = xtgeo.surface_from_file(surfacepath, fformat="irap_binary")
            hillshading = True
            min_val = None
            max_val = None
            color = "viridis"

            s_layer = make_surface_layer(
                surface,
                name="surface",
                min_val=min_val,
                max_val=max_val,
                color=color,
                hillshading=hillshading,
            )
            return [s_layer]

        @app.callback(
            Output(self.ids("cross-section-view"), "figure"),
            [
                Input(self.ids("well-dropdown"), "value"), #wellpath
                Input(self.ids("surfaces-checklist"), "value"), #surfacepaths list
                Input(self.ids("surfaces_de_checklist"), "value"), #surfacepaths_de list
                Input(self.ids("map-view"), "polyline_points"),
            ],
        )
        def _render_xsection(wellpath, surfacepaths, errorpaths, coords):
            ctx = dash.callback_context
            data = []
            if ctx.triggered[0]['prop_id']==self.ids("well-dropdown")+'.value':
                self.xsec.create_well(wellpath,surfacepaths)
            elif ctx.triggered[0]['prop_id']==self.ids("map-view")+'.polyline_points':
                self.xsec.fence = get_fencespec(coords)
                self.xsec.well_attributes = None
            self.xsec.set_surface_lines(surfacepaths)
            self.xsec.set_error_lines(errorpaths)
            data += self.xsec.get_plotly_data(surfacepaths,errorpaths)
            layout = self.xsec.get_plotly_layout(surfacepaths)
            return {'data':data,'layout':layout}

        ### Update of tickboxes when selectin "all" surfaces in cross-section-view
        @app.callback(
            Output(self.ids("surfaces-checklist"), "value"),
            [Input(self.ids("all-surfaces-checkbox"), "value")],
        )
        def update_surface_tickboxes(all_surfaces_checkbox):
            return self.surfacefiles if all_surfaces_checkbox == ['True'] else []

        @app.callback(
            Output(self.ids("modal-graph-settings"), "is_open"),
            [Input(self.ids("button-open-graph-settings"), "n_clicks"),
            Input(self.ids("button-close-graph-settings"), "n_clicks")],
            [State(self.ids("modal-graph-settings"), "is_open")],
        )
        def toggle_modal(n1, n2, is_open):
            if n1 or n2:
                return not is_open
            return is_open

    def add_webvizstore(self):
        return [(get_path, [{"path": fn}]) for fn in self.surfacefiles]

@webvizstore
def get_path(path) -> Path:
    return Path(path)


def get_color(i):
    """
    Returns a list of colors for surface layers
    """
    colors = [
        "rgb(255,0,0)",
        "rgb(255,140,0)",
        "rgb(0,0,255)",
        "rgb(128,128,128)",
        "rgb(255,0,255)",
        "rgb(255,215,0)"
    ]
    n_colors = len(colors)
    return colors[(i)%(n_colors)]

def get_fencespec(coords):
    """Create a XTGeo fence spec from polyline coordinates"""
    poly = xtgeo.Polygons()
    poly.dataframe = pd.DataFrame(
        [
            {
                "X_UTME": c[1],
                "Y_UTMN": c[0],
                "Z_TVDSS": 0,
                "POLY_ID": 1,
                "NAME": "polyline",
            }
            for c in coords
        ]
    )
    return poly.get_fence(asnumpy=True)

