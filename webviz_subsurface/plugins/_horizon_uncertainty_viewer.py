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
from .._datainput.huv_table import FilterTable
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
        self.dataf = FilterTable(self.target_points,self.well_points)
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
                        dbc.Button("Well Settings", id=self.ids("button-open-well-settings")),
                        dbc.Modal(
                            children=[
                                dbc.ModalHeader("Well Settings"),
                                dbc.ModalBody(
                                    children=[
                                        html.Label(
                                            style={
                                                "font-weight": "bold",
                                                "textAlign": "Left",
                                            },
                                            children="Select Well Attributes",
                                        ),
                                        dcc.Checklist(
                                            id=self.ids('all-well-settings-checkbox'),
                                            options=[{'label': 'all', 'value': 'True'}],
                                            value=['True'],
                                        ),
                                        dcc.Checklist(
                                            id=self.ids('well-settings-checklist'),
                                            options=[{"label": "Zonelog", "value": "zonelog"}, 
                                            {"label": "Zonation points", "value": "zonation_points"}, 
                                            {"label": "Conditional points", "value": "conditional_points"}
                                            ],
                                            value=["zonelog", "zonation_points", "conditional_points"]
                                        ),
                                    ],
                                ),
                                dbc.ModalFooter(
                                    children=[
                                        dbc.Button("Close", id=self.ids("button-close-well-settings"),
                                                   className="ml-auto"),
                                        dbc.Button('Apply', id=self.ids('button-apply-well-settings-checklist'),
                                                   className='ml-auto')
                                    ]
                                ),
                            ],
                            id=self.ids("modal-well-settings"),
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
        df = self.dataf.get_targetpoints_datatable()
        return dash_table.DataTable(
            id=self.ids("target-point-table"),
            columns=[{"name": i, "id": i} for i in df.columns],
            data=df.to_dict('records'),
            sort_action="native",
            filter_action="native",
        )

    @property
    def well_points_layout(self):
        return html.Div([
            dbc.Button("Table Settings", id=self.ids("button-open-table-settings")),
            dbc.Modal(
                children=[
                    dbc.ModalHeader("Table Settings"),
                    dbc.ModalBody(
                        children=[
                            html.Label(
                                style={
                                    "font-weight": "bold",
                                    "textAlign": "Left",
                                },
                                children="Select Table Columns",
                            ),
                            dcc.Checklist(
                                id=self.ids('columns-checklist'),
                                options=[
                                    {"label": name, "value": column_name}
                                    for name, column_name in zip(
                                        self.dataf.get_wellpoints_datatable().keys().values, self.dataf.get_wellpoints_datatable().keys().values
                                    )
                                ],
                                value=['Surface', 'Well', 'TVD', 'MD', 'Outlier', 'Deleted', 'Residual']
                            ),
                        ],
                    ),
                    dbc.ModalFooter(
                        children=[
                            dbc.Button("Close", id=self.ids("button-close-table-settings"),
                                        className="ml-auto"),
                            dbc.Button('Apply', id=self.ids('button-apply-columnlist'),
                                        className='ml-auto')
                        ]
                    ),
                ],
                id=self.ids("modal-table-settings"),
                size="sm",
                centered=True,
                backdrop=False,
                fade=False,
            ),
        html.Div(id=self.ids('well-points-table-container')),
        ])
    
    @property
    def depth_error_layout(self):
        return html.Div([
            html.Div(id=self.ids('error_table_container')),
        ])

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
                            html.Div(style={"flex": 1.5}, children=self.cross_section_layout),
                        ]
                    )
                ]
            ),
            dcc.Tab(
                label="TVD uncertainty",
                children=[html.Div(children=self.depth_error_layout)]
            ),
            dcc.Tab(
                label="Target Points",
                children=[html.Div(children=self.target_points_layout)]
            ),
            dcc.Tab(
                label='Well Points',
                children=[self.well_points_layout]
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
                #well_layer = make_well_circle_layer(well, radius = 100, name = well.wellname, color = well_color)
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
                Input(self.ids('button-apply-well-settings-checklist'), 'n_clicks'),
                Input(self.ids("well-dropdown"), "value"),  # wellpath
                Input(self.ids("map-view"), "polyline_points"),  # coordinates from map-view
            ],
            [
                State(self.ids("surfaces-checklist"), "value"),  # surface_paths list
                State(self.ids("surfaces-de-checklist"), "value"),  # error_paths list
                State(self.ids("well-settings-checklist"), "value"),  # well settings checkbox content
            ],
        )
        def _render_xsection(n_clicks, n_clicks2, wellpath, coords, surface_paths, error_paths, well_settings):
            ctx = dash.callback_context
            surface_paths = get_path(surface_paths)
            error_paths = get_path(error_paths)
            if ctx.triggered[0]['prop_id'] == self.ids("well-dropdown") + '.value':
                self.xsec.set_well(wellpath)
            elif ctx.triggered[0]['prop_id'] == self.ids("map-view") + '.polyline_points':
                self.xsec.fence = get_fencespec(coords)
                self.xsec.well_attributes = None
            self.xsec.set_error_and_surface_lines(surface_paths, error_paths)
            self.xsec.set_plotly_fig(surface_paths, error_paths, well_settings)
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

        @app.callback(
            Output(self.ids("well-settings-checklist"), "value"),
            [Input(self.ids("all-well-settings-checkbox"), "value")],
        )
        def _update_well_settings_tickboxes(all_well_attributes_checkbox):
            return ["zonelog", "zonation_points", "conditional_points"] if all_well_attributes_checkbox == ['True'] else []

        @app.callback(
            Output(self.ids("modal-well-settings"), "is_open"),
            [Input(self.ids("button-open-well-settings"), "n_clicks"),
             Input(self.ids("button-close-well-settings"), "n_clicks")],
            [State(self.ids("modal-well-settings"), "is_open")],
        )
        def _toggle_modal_well_settings(n1, n2, is_open):
            if n1 or n2:
                return not is_open
            return is_open


        @app.callback(
            Output(self.ids('well-points-table-container'), 'children'),
            [
                Input(self.ids('button-apply-columnlist'), 'n_clicks'),
            ],
            [
                State(self.ids("columns-checklist"), "value"),  # columns list
            ],
        )
        def display_output(n_clicks, column_list):
            wellpoints_df = self.dataf.update_wellpoints_datatable(column_list)
            return html.Div([
                dash_table.DataTable(
                    id=self.ids('well-points-table'),
                    columns=[{"name": i, "id": i} for i in wellpoints_df.columns],
                    data=wellpoints_df.to_dict('records'),
                    sort_action="native",
                    filter_action="native",
                ),
            ])

        @app.callback(
            Output(self.ids("modal-table-settings"), "is_open"),
            [Input(self.ids("button-open-table-settings"), "n_clicks"),
             Input(self.ids("button-close-table-settings"), "n_clicks")],
            [State(self.ids("modal-table-settings"), "is_open")],
        )
        def _toggle_modal_table_settings(n1, n2, is_open):
            if n1 or n2:
                return not is_open
            return is_open

        @app.callback(
            Output(self.ids("error_table_container"), "children"),
            [
                Input(self.ids("well-dropdown"), "value"),
            ],
        )
        def _render_depth_error_tab(wellpath):
            self.xsec.set_well(wellpath)
            df = self.xsec.get_error_table(wellpath)
            return html.Div([
                dash_table.DataTable(
                    id = self.ids('error_table'),
                    columns = [{'name': i, 'id': i} for i in df.columns],
                    data = df.to_dict('records'),
                )
            ])

    def add_webvizstore(self):
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
        "rgb(70,130,180)", #steel blue
        "rgb(0,0,255)", #blue
        "rgb(51,51,0)", #olive green
        "rgb(0,128,0)", #green
        "rgb(0,255,0)", #lime
        "rgb(255,255,0)", #yellow
        "rgb(255,105,180)", #pink
        "rgb(221,160,221)", #plum
        "rgb(75,0,130)", #purple
        "rgb(160,82,45)", #sienna
        "rgb(244,164,96)", #tan
        "rgb(255,140,0)", #orange
        "rgb(255,69,0)", #blood orange
        "rgb(255,0,0)", #red
        "rgb(220,20,60)", #crimson
        "rgb(128,0,0)", #dark red
        "rgb(101,67,33)", #dark brown
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
