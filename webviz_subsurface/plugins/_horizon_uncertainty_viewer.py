from uuid import uuid4
from pathlib import Path
import dash
import dash_table
import xtgeo
import os
import pandas as pd
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc

import webviz_core_components as wcc
import webviz_subsurface_components
from webviz_config import WebvizPluginABC
from webviz_config.webviz_store import webvizstore

from .._datainput.surface import new_make_surface_layer
from .._datainput.huv_xsection import HuvXsection
from .._datainput.huv_table import FilterTable
from .._datainput import parse_model_file


class HorizonUncertaintyViewer(WebvizPluginABC):
    """ ### HorizonUncertaintyViewer
Visualizes depth error for surfaces in map view and cross section view.
The cross section is defined by surfacefiles and wellfiles or a polyline.
Polyline drawn interactivly in map view. Files parsed from model_file.xml.
* `surfacefiles`: List of file paths to Irap Binary surfaces
* `surfacefiles_de`: List of file paths to Irap Binary depth error surfaces
* `surfacenames`: Corresponding list of displayed surface names
* `surface_attributes`: Dictionary with data related to all surfaces
* `targetpoints`: Targetpoints from targetpoints.csv
* `wellpoints`: Wellpoints from wellpoints.csv
* `topofzone`: Top of zone from model_file.xml
* `wellfiles`: List of file paths to wells
* `wellnames`: List of well names
* `zonation_data`: zonation_status.csv
* `conditional_data`: Data for conditional points from wellpoints.csv
* `zonelogname`: Name of zone logs from model_file.xml
* `well_attributes`: Dictionary with data related to all wells
* `plotly_theme`: Theme from webviz
* `basedir`: Base directory to model_file.xml
* `zunit`: z-unit for display
"""

    def __init__(
            self,
            app,
            basedir: Path = None,
            planned_wells_dir: Path = None,
            zunit="depth (m)",
            zonemin: int = 1,
    ):

        super().__init__()
        self.zunit = zunit
        self.surfacefiles = parse_model_file.get_surface_files(basedir)
        self.surfacefiles_de = parse_model_file.get_error_files(basedir)
        self.surfacefiles_dr = parse_model_file.get_surface_dr_files(basedir)
        self.surfacefiles_dt = parse_model_file.get_surface_dt_files(basedir)
        self.surfacefiles_dte = parse_model_file.get_surface_dte_files(basedir)
        self.surfacefiles_dre = parse_model_file.get_surface_dre_files(basedir)
        self.surface_attributes = {}
        self.target_points = parse_model_file.get_target_points(basedir)
        self.well_points = parse_model_file.get_well_points(basedir)
        self.surfacenames = parse_model_file.extract_surface_names(basedir)
        self.topofzone = parse_model_file.extract_topofzone_names(basedir)
        for i, surfacefile in enumerate(self.surfacefiles):
            self.surface_attributes[Path(surfacefile)] = {
                "color": get_color(i),
                'order': i,
                "name": self.surfacenames[i], "topofzone": self.topofzone[i],
                "surface": xtgeo.surface_from_file(Path(surfacefile), fformat='irap_binary'),
                "surface_de": xtgeo.surface_from_file(Path(self.surfacefiles_de[i]), fformat='irap_binary'),
                "surface_dt": xtgeo.surface_from_file(Path(self.surfacefiles_dt[i]), fformat="irap_binary") if self.surfacefiles_dt is not None else None,
                "surface_dr": xtgeo.surface_from_file(Path(self.surfacefiles_dr[i]), fformat="irap_binary") if self.surfacefiles_dr is not None else None,
                "surface_dte": xtgeo.surface_from_file(Path(self.surfacefiles_dte[i]), fformat="irap_binary") if self.surfacefiles_dte is not None else None,
                "surface_dre": xtgeo.surface_from_file(Path(self.surfacefiles_dre[i]), fformat="irap_binary") if self.surfacefiles_dre is not None else None,
            }
        self.wellfiles = parse_model_file.get_well_files(basedir)
        self.wellnames = [Path(wellfile).stem for wellfile in self.wellfiles]
        self.zonation_data = parse_model_file.get_zonation_data(basedir)
        self.conditional_data = parse_model_file.get_conditional_data(basedir)
        self.zonemin = zonemin
        self.zonelog_name = parse_model_file.get_zonelog_name(basedir)  # name of zonelog in OP txt files
        self.plotly_theme = app.webviz_settings["theme"].plotly_theme
        self.uid = uuid4()
        self.set_callbacks(app)
        self.xsec = HuvXsection(self.surface_attributes, self.zonation_data, self.conditional_data, self.zonelog_name)
        self.df_well_target_points = FilterTable(self.target_points, self.well_points)
        if planned_wells_dir is not None:
            self.planned_well_files = [os.path.join(planned_wells_dir, f) for f in os.listdir(planned_wells_dir)]
            self.planned_wells = [xtgeo.well_from_file(wf) for wf in self.planned_well_files]
            self.planned_well_names = [Path(wf).stem for wf in self.planned_well_files]
        else:
            self.planned_well_files = None
            self.planned_wells = None
            self.planned_well_names = None
        self.xsec.set_well_attributes(self.wellfiles)

        # Store current layers
        self.LAYERS_STATE = []
        self.state = {
            'switch': True
        }

    def ids(self, element):
        return f"{element}-id-{self.uid}"

    @property
    def cross_section_graph_layout(self):
        return html.Div(
            children=[
                wcc.Graph(
                    id=self.ids("xsec-view"),
                )
            ]
        )

    @property
    def cross_section_widgets_layout(self):
        return html.Div(
            children=[
                html.Div(
                    children=[
                        dbc.Button(
                            "Graph Settings",
                            id=self.ids("button-open-graph-settings"),
                            color='light',
                            className='mr-1'
                        ),
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
                                                {
                                                    "label": name + '_depth_error',
                                                    "value": path,
                                                    "disabled": False
                                                }
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
                                        dbc.Button(
                                            "Close",
                                            id=self.ids("button-close-graph-settings"),
                                            className="ml-auto"
                                        ),
                                        dbc.Button(
                                            'Apply changes',
                                            id=self.ids('button-apply-checklist'),
                                            className='ml-auto'
                                        )
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
                                            options=[
                                                {
                                                    "label": "Zonelog",
                                                    "value": "zonelog"
                                                },
                                                {
                                                    "label": "Zonation points",
                                                    "value": "zonation_points"
                                                },
                                                {
                                                    "label": "Conditional points",
                                                    "value": "conditional_points"
                                                }
                                            ],
                                            value=[
                                                "zonelog",
                                                "zonation_points",
                                                "conditional_points"
                                            ]
                                        ),
                                    ],
                                ),
                                dbc.ModalFooter(
                                    children=[
                                        dbc.Button(
                                            "Close",
                                            id=self.ids("button-close-well-settings"),
                                            className="ml-auto"
                                        ),
                                        dbc.Button(
                                            'Apply',
                                            id=self.ids('button-apply-well-settings-checklist'),
                                            className='ml-auto'
                                        )
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
                                    ] + [
                                        {'label': name, 'value': path}
                                        for name, path in zip(self.planned_well_names, self.planned_well_files)
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
                        html.Div(
                            style={
                                "marginTop": "0px",
                                "height": "800px",
                                "zIndex": -9999,
                            },
                            children=[self.cross_section_graph_layout],
                            id=self.ids("cross-section-view"),
                        )
                    ]
                ),
            ]
        )

    @property
    def target_points_tab_layout(self):
        df = self.df_well_target_points.get_targetpoints_df()
        return dash_table.DataTable(
            id=self.ids("target-point-table"),
            columns=[{"name": i, "id": i} for i in df.columns],
            data=df.to_dict('records'),
            sort_action="native",
            filter_action="native",
        )

    @property
    def well_points_tab_layout(self):
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
                                        self.df_well_target_points.get_wellpoints_df().keys().values,
                                        self.df_well_target_points.get_wellpoints_df().keys().values
                                    )
                                ],
                                value=[
                                    'Surface',
                                    'Well',
                                    'TVD',
                                    'MD',
                                    'Outlier',
                                    'Deleted',
                                    'Residual'
                                ]
                            ),
                        ],
                    ),
                    dbc.ModalFooter(
                        children=[
                            dbc.Button(
                                "Close",
                                id=self.ids("button-close-table-settings"),
                                className="ml-auto"
                            ),
                            dbc.Button(
                                'Apply',
                                id=self.ids('button-apply-columnlist'),
                                className='ml-auto'
                            )
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
    def left_flexbox_layout(self):
        return html.Div(
            children=[
                html.Div(id=self.ids('hidden-div-map-view'), children=[self.map_view_layout], style={'display': 'none'}),  # Hidden div to store polyline points when in table view
                html.Div(id=self.ids('hidden-div-table-view'), children=[self.table_view_layout], style={'display': 'none'}),
                wcc.FlexBox(
                    children=[
                        dcc.RadioItems(
                            options=[
                                {'label': 'Map view', 'value': 'map-view'},
                                {'label': 'Table view', 'value': 'table-view'}
                            ],
                            id=self.ids('map-table-radioitems'),
                            value='map-view'
                        )
                    ]
                ),
                html.Div(
                    id=self.ids('left-flexbox-content'),
                )
            ]
        )

    @property
    def map_view_layout(self):
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
                                            self.surfacenames, self.surfacefiles
                                        )
                                    ],
                                    value=self.surfacefiles[0],
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
                    children=[
                        webviz_subsurface_components.NewLayeredMap(
                            id=self.ids("layered-map"),
                            layers=[],
                            syncedMaps=[],
                            minZoom=-5,
                            drawTools={
                                "drawMarker": False,
                                "drawPolygon": False,
                                "drawPolyline": True,
                                "position": "topright"
                            },
                            switch={
                                "value": self.state['switch'],
                                "label": "Hillshading",
                            },
                            colorBar={
                                "position": "bottomright"
                            },
                        ),
                    ],
                )
            ]
        )

    @property
    def table_view_layout(self):
        df = self.xsec.get_intersection_dataframe(self.wellfiles[0])
        return html.Div(
            children=[
                dash_table.DataTable(
                    id=self.ids('uncertainty-table'),
                    columns=[{"name": i, "id": i} for i in df.columns],
                    data=df.to_dict('records')
                )
            ]
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
                            html.Div(style={"flex": 1}, children=self.left_flexbox_layout),
                            html.Div(style={"flex": 1.5}, children=self.cross_section_widgets_layout),
                        ]
                    )
                ]
            ),
            dcc.Tab(
                label="Target Points",
                children=[html.Div(children=self.target_points_tab_layout)]
            ),
            dcc.Tab(
                label='Well Points',
                children=[self.well_points_tab_layout]
            )
        ])

    def set_callbacks(self, app):
        @app.callback(
            Output(self.ids("layered-map"), "layers"),
            [
                Input(self.ids("map-dropdown"), "value"),
                Input(self.ids("layered-map"), "switch")
            ],
        )
        def _render_map(surfacefile, switch):
            ''' Renders map view with depth error '''
            if self.state['switch'] is not switch['value']:
                new_layers = self.LAYERS_STATE.copy()
                for layer in new_layers:
                    if "shader" in layer["data"][0]:
                        layer["data"][0]["shader"]["type"] = 'hillshading' if switch['value'] is True else None  # soft-hillshading
                        layer["action"] = "update"
                self.state['switch'] = switch['value']
                return new_layers
            surface_name = self.surface_attributes[Path(surfacefile)]["name"]
            shader_type = 'hillshading' if switch['value'] is True else None  # soft-hillshading
            min_val = None
            max_val = None
            color = ["#0d0887", "#46039f", "#7201a8", "#9c179e", "#bd3786", "#d8576b", "#ed7953", "#fb9f3a", "#fdca26", "#f0f921"]
            well_layers = []
            for wellfile in self.wellfiles:
                well = xtgeo.Well(Path(wellfile))
                well_layer_dict = make_well_circle_layer(well.wellname, self.conditional_data, surface_name, radius=100, color="rgb(0,255,0)")
                if len(well_layer_dict["data"]) != 0:
                    well_layer_dict["id"] = surface_name + ' ' + well.wellname + "-id"
                    well_layer_dict["action"] = "add"
                    well_layers.append(well_layer_dict)
            surfaces = [
                        self.surface_attributes[Path(surfacefile)]["surface_dt"],
                        self.surface_attributes[Path(surfacefile)]["surface_dte"],
                        self.surface_attributes[Path(surfacefile)]["surface_dr"],
                        self.surface_attributes[Path(surfacefile)]["surface_dre"],
                        self.surface_attributes[Path(surfacefile)]["surface_de"],
                        self.surface_attributes[Path(surfacefile)]["surface"]
            ]
            d_list = [
                        "Depth trend",
                        "Depth trend uncertainty",
                        "Depth residual",
                        "Depth residual uncertainty",
                        "Depth uncertainty",
                        "Depth"
            ]
            layers = []
            for i, sfc in enumerate(surfaces):
                if sfc is not None:
                    s_layer = new_make_surface_layer(
                        sfc,
                        name=d_list[i],
                        min_val=min_val,
                        max_val=max_val,
                        color=color,
                        shader_type=shader_type,
                    )
                    s_layer["id"] = surface_name + ' ' + d_list[i] + "-id"
                    s_layer["action"] = "add"
                    layers.append(s_layer)
            layers.extend(well_layers)
            # Deletes old layers
            old_layers = self.LAYERS_STATE
            self.LAYERS_STATE = layers.copy()
            if old_layers is not None and len(old_layers) > 0:
                for layer in old_layers:
                    layer["action"] = "delete"
                layers.extend(old_layers)
            return layers

        @app.callback(
            Output(self.ids("xsec-view"), "figure"),
            [
                Input(self.ids('button-apply-checklist'), 'n_clicks'),
                Input(self.ids('button-apply-well-settings-checklist'), 'n_clicks'),
                Input(self.ids("well-dropdown"), "value"),  # wellpath
                Input(self.ids("layered-map"), "polyline_points"),  # coordinates from layered-map
            ],
            [
                State(self.ids("surfaces-checklist"), "value"),  # List of surfacefiles
                State(self.ids("surfaces-de-checklist"), "value"),  # List of surfacefiles keys
                State(self.ids("well-settings-checklist"), "value"),  # Well settings checkbox content
            ],
        )
        def _render_xsection(n_clicks, n_clicks2, wellfile, polyline, surfacefiles, de_keys, well_settings):
            ''' Renders cross section view from wellfile or polyline drawn in map view '''
            ctx = dash.callback_context
            de_keys = get_path(de_keys)
            surfacefiles = get_path(surfacefiles)
            if ctx.triggered[0]['prop_id'] == self.ids('layered-map') + '.polyline_points' and polyline is not None:
                wellpath = None
            self.xsec.set_de_and_surface_lines(surfacefiles, de_keys, wellfile, polyline)
            self.xsec.set_xsec_fig(surfacefiles, de_keys, well_settings, wellfile)
            return self.xsec.fig

        @app.callback(
            Output(self.ids("surfaces-checklist"), "value"),
            [Input(self.ids("all-surfaces-checkbox"), "value")],
        )
        def _update_surface_tickboxes(all_surfaces_checkbox):
            ''' Toggle on/off all surfaces in graph settings modal '''
            return self.surfacefiles if all_surfaces_checkbox == ['True'] else []

        @app.callback(
            Output(self.ids("modal-graph-settings"), "is_open"),
            [
                Input(self.ids("button-open-graph-settings"), "n_clicks"),
                Input(self.ids("button-close-graph-settings"), "n_clicks"),
                Input(self.ids('button-open-graph-settings'), 'disabled')
            ],
            [State(self.ids("modal-graph-settings"), "is_open")],
        )
        def _toggle_modal_graph_settings(n1, n2, disabled, is_open):
            ''' Open or close graph settings modal button '''
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
            ''' Removes ability to toggle depth error when corresponding surface is disabled in graph settings modal '''
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
            return [
                "zonelog",
                "zonation_points",
                "conditional_points"
            ] if all_well_attributes_checkbox == ['True'] else []

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
            wellpoints_df = self.df_well_target_points.update_wellpoints_df(column_list)
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
            Output(self.ids('left-flexbox-content'), 'children'),
            [
                Input(self.ids('map-table-radioitems'), 'value'),
                Input(self.ids('hidden-div-map-view'), 'children'),
                Input(self.ids('hidden-div-table-view'), 'children')
            ]
        )
        def _toggle_left_flexbox_content(value, map_view_content, table_view_content):
            if value == 'table-view':
                return table_view_content
            else:
                return map_view_content



        @app.callback(
            Output(self.ids('uncertainty-table'), 'data'),
            [Input(self.ids('well-dropdown'), 'value')]
        )
        def _render_uncertainty_table(wellfile):
            df = self.xsec.get_intersection_dataframe(wellfile)
            return df.to_dict('records')

    def add_webvizstore(self):
        return [(get_path, [{"paths": fn}]) for fn in self.surfacefiles]


@webvizstore
def get_path(paths) -> Path:
    for i, path in enumerate(paths):
        paths[i] = Path(path)
    return paths


def get_color(i):
    """ Create a list of colors for surface layers
    Args:
        i: Index of surface layer in surfacefiles list
    Returns:
        List of colors for surface layers
    """
    colors = [
        "rgb(70,130,180)",      # Steel blue
        "rgb(0,0,255)",         # Blue
        "rgb(51,51,0)",         # Olive green
        "rgb(0,128,0)",         # Green
        "rgb(0,255,0)",         # Lime
        "rgb(255,255,0)",       # Yellow
        "rgb(255,105,180)",     # Pink
        "rgb(221,160,221)",     # Plum
        "rgb(75,0,130)",        # Purple
        "rgb(160,82,45)",       # Sienna
        "rgb(244,164,96)",      # Tan
        "rgb(255,140,0)",       # Orange
        "rgb(255,69,0)",        # Blood orange
        "rgb(255,0,0)",         # Red
        "rgb(220,20,60)",       # Crimson
        "rgb(128,0,0)",         # Dark red
        "rgb(101,67,33)",       # Dark brown
    ]
    n_colors = len(colors)
    return colors[(i) % (n_colors)]


def make_well_circle_layer(well_name, cond_path, surface_name, radius=1000, color="red"):
    """ Make circles around well in layered map view
    Args:
        well_name: Name of well
        cond_path: Path to wellpoints.csv
        surface_name: Name of surface
    Returns:
        Dictionary with data
     """
    conditional_data = pd.read_csv(cond_path)
    cond_df = conditional_data[conditional_data["Surface"] == surface_name]
    well_cond_df = cond_df[cond_df["Well"] == well_name]
    coord = well_cond_df[['x', 'y']].values
    if len(coord) == 0:
        return {
            "name": well_name,
            "checked": True,
            "baseLayer": False,
            "data": [],
        }
    if len(coord) != 0:
        return {
            "name": well_name,
            "checked": True,
            "baseLayer": False,
            "data": [{
                "type": "circle",
                "center": coord[0],
                "color": color,
                "radius": radius,
                "tooltip": well_name,
            }],
        }
