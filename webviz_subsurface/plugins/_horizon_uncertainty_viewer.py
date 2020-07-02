from uuid import uuid4
from pathlib import Path
from typing import List
import dash
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
from operator import add
from operator import sub

from .._datainput.well import load_well
from .._datainput.surface import make_surface_layer, get_surface_fence, load_surface


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
        #surface_attributes: None,
        wellfiles: List[Path],
        surfacenames: list = None,
        wellnames: list = None,
        zonelog: str = None,
        zunit="depth (m)",
        zonemin: int = 1,
        colordict = None,
    ):

        super().__init__()
        self.zunit = zunit
        self.surfacefiles = [str(surffile) for surffile in surfacefiles]
        self.surfacefiles_de = [str(surfacefile_de) for surfacefile_de in surfacefiles_de]
        self.surface_attributes = {x: {} for x in surfacefiles}
        
        for i, surfacefile in enumerate(surfacefiles):
            self.surface_attributes[surfacefile] = {"color": get_color(i), "errorpath": surfacefiles_de[i]}

        if surfacenames is not None:
            if len(surfacenames) != len(surfacefiles):
                raise ValueError(
                    "List of surface names specified should be same length as list of surfacefiles"
                )
            self.surfacenames = surfacenames
        else:
            self.surfacenames = [Path(surfacefile).stem for surfacefile in surfacefiles]
        if colordict is not None:
            if len(colordict)!=len(surfacefiles):
                raise ValueError(
                    "colordict should be the same length as list of surfacefiles"
                )
            self.colordict = colordict
        else:
            self.colordict={surfacefile:get_color(i) for i, surfacefile in enumerate(surfacefiles)}
        self.wellfiles = [str(wellfile) for wellfile in wellfiles]
        if wellnames is not None:
            if len(wellnames) != len(wellfiles):
                raise ValueError(
                    "List of surface names specified should be same length as list of surfacefiles"
                )
            self.wellnames = wellnames
        else:
            self.wellnames = [Path(wellfile).stem for wellfile in wellfiles]
        self.zonemin = zonemin
        self.zonelog = zonelog       
        self.plotly_theme = app.webviz_settings["theme"].plotly_theme
        self.uid = uuid4()
        self.set_callbacks(app)

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

    ### Flexbox ###
    @property
    def layout(self):
        return wcc.FlexBox(
            id=self.ids("layout"),
            children=[
                html.Div(style={"flex": 1}, children=self.map_layout),
                html.Div(style={"flex": 1}, children=self.cross_section_layout),
            ],
        )

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
        def _render_surface(wellpath, surfacepaths, surfacepaths_de, coords):
            ctx = dash.callback_context
            print(ctx.triggered[0]['prop_id']==self.ids("well-dropdown")+'.value')
            print(ctx.triggered[0]['prop_id']==self.ids("surfaces-checklist")+'.value')
            print(ctx.triggered[0]['prop_id']==self.ids("map-view")+'.polyline_points')

            well = xtgeo.Well(get_path(wellpath))
            well_df = well.dataframe
            well_fence = well.get_fence_polyline(nextend=100, sampling=5) # Generate a polyline along a well path
            well.create_relative_hlen() # Get surface values along the polyline

            surfaces = []
            surfaces_lines = []
            surfaces_lines_ydata = []

            for idx, path in enumerate(surfacepaths): # surface
                surfaces.append(xtgeo.surface_from_file(path, fformat="irap_binary")) #list of surfaces
                surfaces_lines.append(surfaces[idx].get_randomline(well_fence)) # cross section x and y coordinates

            surfaces_de = []
            surfaces_lines_de = []
            surfaces_lines_de_xdata = []
            surfaces_lines_de_add_ydata = []
            surfaces_lines_de_sub_ydata = []

            for idx, path in enumerate(surfacepaths_de): # surface with depth error
                surfaces_de.append(xtgeo.surface_from_file(path, fformat="irap_binary")) #list of surfaces
                surfaces_lines_de.append(surfaces_de[idx].get_randomline(well_fence)) # cross section x and y coordinates
                surfaces_lines_de_xdata.append(surfaces_lines_de[idx][:,0]) # x coordinates lines from surface
                surfaces_lines_de_add_ydata.append(list(map(add, surfaces_lines[idx][:,1], surfaces_lines_de[idx][:,1]))) #add error y data
                surfaces_lines_de_sub_ydata.append(list(map(sub, surfaces_lines[idx][:,1], surfaces_lines_de[idx][:,1]))) #sub error y data

            surfacetuples = [(surfacepath,surface_line) for surfacepath, surface_line in zip(surfacepaths, surfaces_lines)]
            def depth_sort(elem):
                return np.min(elem[1][:,1])
            surfacetuples.sort(key=depth_sort, reverse=True)

            return make_gofig(well_df, surfaces_lines, surfaces_lines_de_add_ydata, surfaces_lines_de_sub_ydata, surfaces_lines_de_xdata, self.colordict, surfacetuples)

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

def make_gofig(well_df, surfaces_lines, surfaces_lines_de_add_ydata, surfaces_lines_de_sub_ydata, surfaces_lines_de_xdata, colordict, surfacetuples):
    max_depth = max_depth_of_surflines(surfaces_lines)
    min_depth = min_depth_of_surflines(surfaces_lines)
    x_well,y_well,xmax = find_where_it_crosses_well(min_depth,max_depth,well_df)
    y_width = np.abs(max_depth-y_well)
    x_width = np.abs(xmax-x_well)
    zvals = well_df["Z_TVDSS"].values.copy()
    hvals = well_df["R_HLEN"].values.copy()
    zoneplot = plot_well_zonelog(well_df,zvals,hvals,"Zonelog",-999)
    layout = {}
    layout.update(
        {          
            "yaxis": {
                "title": "Depth (m)",
                "autorange": "off",
                "range" : [max_depth,y_well-0.15*y_width]
            },
            "xaxis": {
                "title": "Distance from polyline",
                "range": [x_well-0.5*x_width,xmax+0.5*x_width],
            },
            "plot_bgcolor":'rgb(233,233,233)',
            "showlegend":False,
            "height": 830,
        }
    )
   
    
    data_surfaces_de_add = [{
                "type": "line",
                "y": ydata,
                "x": surfaces_lines_de_xdata[idx],
                "name": "error_add",
                "line":{"color":"black"},
            } for idx, ydata in enumerate(surfaces_lines_de_add_ydata)
            ]
    data_surfaces_de_sub = [{
                "type": "line",
                "y": ydata,
                "x": surfaces_lines_de_xdata[idx],
                "name": "error_sub",
                "line":{"color":"gray"},
            } for idx, ydata in enumerate(surfaces_lines_de_sub_ydata)
            ]
    data_surfaces = [
        {
            "type": "line",
            "x": [surfaces_lines[0][0, 0], surfaces_lines[0][np.shape(surfaces_lines[0])[0] - 1, 0]],
            "y": [max_depth + 50, max_depth + 50],
            "line": {"color": "rgba(0,0,0,1)", "width": 0.6},
        }
    ]
    data_surfaces += [
        {
        "type": "line",
        "y": surface_line[:, 1],
        "x": surface_line[:, 0],
        "name": "surface",
        "fill": "tonexty",
        "line": {"color": "rgba(0,0,0,1)", "width": 0.6},
        "fillcolor": colordict[Path(surfacepath)]
        }
        for surfacepath, surface_line in surfacetuples
    ]
    
    data_surfaces.append({
                "type": "line",
                "y": well_df["Z_TVDSS"],
                "x": well_df["R_HLEN"],
                "name": "well"
                })
    data1 = zoneplot
    return {'data':data_surfaces + data_surfaces_de_add + data_surfaces_de_sub + data1,
            'layout':layout}

def max_depth_of_surflines(surfaces_lines):
    """
    Find the maximum depth of layers along a cross section
    :param surfaces_lines: surface cross section lines
    :return: max depth
    """
    maxvalues = np.array([
        np.max(sl[:,1]) for sl in surfaces_lines
    ])
    return np.max(maxvalues)

def min_depth_of_surflines(surfaces_lines):
    """
    Find the minimum depth of layers along a cross section
    :param surfaces_lines: surface cross section lines
    :return: min depth
    """
    minvalues = np.array([
        np.min(sl[:,1]) for sl in surfaces_lines
    ])
    return np.min(minvalues)

def find_where_it_crosses_well(ymin,ymax,df):
    y_well = df["Z_TVDSS"]
    x_well = df["R_HLEN"]
    x_well_max = np.max(x_well)
    X_point_y = 0
    X_point_x = 0
    for i in range(len(y_well)):
        if y_well[i] >= ymin:
            X_point_y = y_well[i]
            X_point_x = x_well[i]
            break
    return X_point_x, X_point_y, x_well_max

def plot_well_zonelog(df,zvals,hvals,zonelogname="Zonelog",zomin=-999):
    if zonelogname not in df.columns:
        return
    zonevals = df[zonelogname].values #values of zonelog
    zomin = (
        zomin if zomin >= int(df[zonelogname].min()) else int(df[zonelogname].min())
    ) #zomin=0 in this case
    zomax = int(df[zonelogname].max()) #zomax = 4 in this case
    # To prevent gaps in the zonelog it is necessary to duplicate each zone transition
    zone_transitions = np.where(zonevals[:-1] != zonevals[1:]) #index of zone transitions?
    for transition in zone_transitions:
        try:
            zvals = np.insert(zvals, transition, zvals[transition + 1])
            hvals = np.insert(hvals, transition, hvals[transition + 1])
            zonevals = np.insert(zonevals, transition, zonevals[transition])
        except IndexError:
            pass
    zoneplot = []
    color = ["yellow","orange","green","red","grey"]
    for i, zone in enumerate(range(zomin, zomax + 1)):
        zvals_copy = ma.masked_where(zonevals != zone, zvals)
        hvals_copy = ma.masked_where(zonevals != zone, hvals)
        zoneplot.append({
            "x": hvals_copy.compressed(),
            "y": zvals_copy.compressed(),
            "line": {"width": 5, "color": color[i]},
            "fillcolor": color[i],
            "marker": {"opacity": 0.5},
            "name": f"Zone: {zone}",
        })
    return zoneplot

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
