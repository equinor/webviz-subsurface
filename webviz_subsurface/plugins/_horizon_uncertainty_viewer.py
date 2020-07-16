from uuid import uuid4
from pathlib import Path
from typing import List
import os
import base64
import dash
import dash_table
import pandas as pd
import numpy as np
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
from .._datainput import parse_model_file


class HorizonUncertaintyViewer(WebvizPluginABC):
    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
    app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
    # app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    """
This plugin visualizes surfaces in a map view and seismic in a cross section view.
The cross section is defined by a polyline interactively edited in the map view.
* `surfacefiles`: List of file paths to Irap Binary surfaces
* `surfacenames`: Corresponding list of displayed surface names
* `zunit`: z-unit for display
* `colors`: List of colors to use
"""

    def __init__(
            self,
            app,
            basedir: List[Path],
            zunit="depth (m)",
            zonemin: int = 1,
    ):

        super().__init__()
        self.zunit = zunit
        self.surfacefiles = parse_model_file.get_surface_files(basedir[0])
        self.surfacefiles_de = parse_model_file.get_error_files(basedir[0])
        self.surface_attributes = {}
        self.target_points = parse_model_file.get_target_points(basedir[0])
        self.well_points = parse_model_file.get_well_points(basedir[0])
        self.surfacenames = parse_model_file.extract_surface_names(basedir[0])
        self.topofzone = parse_model_file.extract_topofzone_names(basedir[0])
        for i, surfacefile in enumerate(self.surfacefiles):
            self.surface_attributes[Path(surfacefile)] = {"color": get_color(i), 'order': i,
                                                          "name": self.surfacenames[i], "topofzone": self.topofzone[i],
                                                          "error_path": Path(self.surfacefiles_de[i])}
        self.wellfiles = parse_model_file.get_well_files(basedir[0])
        self.wellnames = [Path(wellfile).stem for wellfile in self.wellfiles]
        self.zonation_data = parse_model_file.get_zonation_data(basedir[0])
        self.conditional_data = parse_model_file.get_conditional_data(basedir[0])
        self.zonemin = zonemin
        self.zonelog_name = parse_model_file.get_zonelog_name(basedir[0])  # name of zonelog in OP txt files
        self.plotly_theme = app.webviz_settings["theme"].plotly_theme
        self.uid = uuid4()
        self.set_callbacks(app)
        self.xsec = HuvXsection(self.surface_attributes, self.zonation_data, self.conditional_data, self.zonelog_name)
        self.xsec.set_well(self.wellfiles[0])

    def ids(self, element):
        return f"{element}-id-{self.uid}"

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


    @property
    def plotly_layout(self):
        return html.Div(
            children=[
                wcc.Graph(
                    id=self.ids("plotly-view"),
                )
            ]
        )

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
                                    disabled=False,
                                ),
                            ]
                        ),
                    ],
                ),
                html.Div(
                    children=[
                        dbc.Button("Graph Settings", id=self.ids("button-open-graph-settings"), color='light', className='mr-1'),
                        dbc.Button('Draw well', id=self.ids('button-draw-well'), color='light', className='mr-1'),
                        dbc.Button('Done', id=self.ids('button-done-draw-well'), className='mr-1', color='light'),
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
                                            id=self.ids('surfaces-de-checklist'),
                                            options=[
                                                {"label": name + '_error', "value": path, 'disabled': False}
                                                for name, path in zip(
                                                    self.surfacenames, self.surfacefiles
                                                )
                                            ],
                                            value=self.surfacefiles,
                                        ),
                                    ],
                                ),
                                dbc.ModalFooter(
                                    children=[
                                        dbc.Button("Close", id=self.ids("button-close-graph-settings"),
                                                   className="ml-auto"),
                                        dbc.Button('Apply changes', id=self.ids('button-apply-checklist'),
                                                   className='ml-auto')
                                    ]
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
                            children=[self.plotly_layout],
                            id=self.ids("cross-section-view"),
                        )
                    ]
                ),
            ]
        )

    @property
    def target_points_layout(self):
        df = pd.read_csv(self.target_points)
        return dash_table.DataTable(
            id=self.ids("target_point_table"),
            columns=[{"name": i, "id": i} for i in df.columns],
            data=df.to_dict('records'),
        )

    @property
    def well_points_layout(self):
        df = pd.read_csv(self.well_points)
        return dash_table.DataTable(
            id=self.ids("well_points_table"),
            columns=[{"name": i, "id": i} for i in df.columns],
            data=df.to_dict('records')
        )

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
                label="Target Points",
                children=[html.Div(children=self.target_points_layout)]
            ),
            dcc.Tab(
                label='Well Points',
                children=[html.Div(children=self.well_points_layout)]
            )
        ])

    def set_callbacks(self, app):
        @app.callback(
            Output(self.ids("map-view"), "layers"),
            [
                Input(self.ids("map-dropdown"), "value"),
            ],
        )
        def _render_map(error_path):
            surface = xtgeo.surface_from_file(error_path, fformat="irap_binary")
            hillshading = True
            min_val = None
            max_val = None
            color = "magma"
            well_layers = []
            for wellpath in self.wellfiles:
                if str(self.xsec.well_attributes["wellpath"]) == wellpath:
                    well_color = "green"
                else:
                    well_color = "black"
                well = xtgeo.Well(Path(wellpath))
                well_layer = make_well_polyline_layer(well, well.wellname, color=well_color)
                well_layers.append(well_layer)

            s_layer = make_surface_layer(
                surface,
                name="surface",
                min_val=min_val,
                max_val=max_val,
                color=color,
                hillshading=hillshading,
            )
            layers = [s_layer]
            #layers.extend(well_layers)
            return layers

        @app.callback(
            Output(self.ids("plotly-view"), "figure"),
            [
                Input(self.ids('button-apply-checklist'), 'n_clicks'),
                Input(self.ids("well-dropdown"), "value"),  # wellpath
                Input(self.ids("map-view"), "polyline_points"),  # coordinates from map-view
                Input(self.ids('plotly-view'), 'clickData'),
            ],
            [
                State(self.ids("surfaces-checklist"), "value"),  # surface_paths list
                State(self.ids("surfaces-de-checklist"), "value"),  # error_paths list
            ],
        )
        def _render_xsection(n_clicks, wellpath, coords, click_data, surface_paths, error_paths):
            ctx = dash.callback_context
            surface_paths = get_path(surface_paths)
            error_paths = get_path(error_paths)
            if ctx.triggered[0]['prop_id'] == self.ids("well-dropdown") + '.value':
                self.xsec.set_well(wellpath)
            elif ctx.triggered[0]['prop_id'] == self.ids("map-view") + '.polyline_points':
                self.xsec.fence = get_fencespec(coords)
                self.xsec.well_attributes = None
            if ctx.triggered[0]['prop_id'] == self.ids('plotly-view') + '.clickData':
                self.xsec.add_freehand_point(click_data)
            else:
                self.xsec.set_error_and_surface_lines(surface_paths, error_paths)
                self.xsec.set_plotly_fig(surface_paths, error_paths)
            return self.xsec.fig

        @app.callback(
            Output(self.ids("surfaces-checklist"), "value"),
            [Input(self.ids("all-surfaces-checkbox"), "value")],
        )
        def _update_surface_tickboxes(all_surfaces_checkbox):
            return self.surfacefiles if all_surfaces_checkbox == ['True'] else []


        @app.callback(
            Output(self.ids("modal-graph-settings"), "is_open"),
            [Input(self.ids("button-open-graph-settings"), "n_clicks"),
             Input(self.ids("button-close-graph-settings"), "n_clicks"),
             Input(self.ids('button-open-graph-settings'), 'disabled')],
            [State(self.ids("modal-graph-settings"), "is_open")],
        )
        def _toggle_modal(n1, n2, disabled, is_open):
            if disabled:
                return False
            elif n1 or n2:
                return not is_open
            else:
                return is_open


        @app.callback(
            [Output(self.ids('button-open-graph-settings'), 'disabled'),
             Output(self.ids('button-done-draw-well'), 'disabled'),
             Output(self.ids('button-open-graph-settings'), 'children')],
            [Input(self.ids('button-draw-well'), 'n_clicks')],
            [State(self.ids('button-open-graph-settings'), 'disabled')]
        )
        def _draw_well(n_clicks, disabled_graph_settings):
            if disabled_graph_settings:
                children = 'Graph settings'
            else:
                children = 'Disabled'
            disabled_done = disabled_graph_settings
            return not disabled_graph_settings, disabled_done, children


        @app.callback(
            Output(self.ids('surfaces-de-checklist'), 'options'),
            [Input(self.ids('surfaces-checklist'), 'value')],
            [State(self.ids('surfaces-de-checklist'), 'options')],
        )
        def _disable_error_checkboxes(surface_values, de_options):
            for i, opt in enumerate(de_options):
                if (surface_values is None) or (opt['value'] not in surface_values):
                    de_options[i]['disabled'] = True
                else:
                    de_options[i]['disabled'] = False
            return de_options

    def add_webvizstore(self):
        print('This function doesnt do anything, does it?')
        return [(get_path, [{"paths": fn}]) for fn in self.surfacefiles]


@webvizstore
def get_path(paths) -> Path:
    for i, path in enumerate(paths):
        paths[i] = Path(path)
    return paths


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
    return colors[(i) % (n_colors)]


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

def make_png_layer(img_bytes, base_layer=True):
    encoded = base64.b64encode(img_bytes).decode()
    img_base64 = "data:image/png;base64,{}".format(encoded)
    return {
        "name": "Draw well view",
        "checked": base_layer,
        "base_layer": True,
        "data": [
            {
                "type": "image",
                "url": img_base64,
                "bounds": [[1, 2], [10, 20]],
            }
        ],
    }

def make_well_polyline_layer(well, name="well", zmin=0, base_layer=False, color="black"):
    """Make LayeredMap well polyline"""
    well.dataframe = well.dataframe[well.dataframe["Z_TVDSS"] > zmin]
    positions = well.dataframe[["X_UTME", "Y_UTMN"]].values
    return {
        "name": name,
        "checked": True,
        "base_layer": base_layer,
        "data": [
            {
                "type": "polyline",
                "color": color,
                "positions": positions,
                "tooltip": name,
            }
        ],
    }

def make_well_circle_layer(well, radius=1000, name="well", base_layer=False, color="red"):
    """Make LayeredMap circle"""
    well.dataframe = well.dataframe[well.dataframe["Z_TVDSS"] > 0]
    coord = well.dataframe[["X_UTME", "Y_UTMN"]].values
    return {
        "name": name,
        "checked": True,
        "base_layer": base_layer,
        "data": [
            {
                "type": "circle",
                "center": coord[0],
                "color": color,
                "radius": radius,
                "tooltip": name,
            }
        ],
    }
