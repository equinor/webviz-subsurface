# pylint: disable=too-many-lines
import io
import json
from pathlib import Path
from typing import Callable, List, Tuple
from uuid import uuid4

import dash_bootstrap_components as dbc
import defusedxml.ElementTree as ET
import numpy as np
import webviz_core_components as wcc
import webviz_subsurface_components
import xtgeo
from dash import Dash, Input, Output, State, callback_context, dash_table, dcc, html
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.deprecation_decorators import deprecated_plugin
from webviz_config.webviz_assets import WEBVIZ_ASSETS
from webviz_config.webviz_store import webvizstore

import webviz_subsurface
from webviz_subsurface._datainput.well import get_well_layers
from webviz_subsurface._models import SurfaceLeafletModel

from ._huv_table import FilterTable
from ._huv_xsection import HuvXsection


@deprecated_plugin(
    "Relevant functionality is implemented in the StructuralUncertainty plugin."
)
class HorizonUncertaintyViewer(WebvizPluginABC):
    """Visualizes depth uncertainty for surfaces in map view and cross section view.

    The cross section is defined by wellfiles and surfacefiles or a polyline.
    Polylines are drawn interactivly in map view.

    !> The plugin reads information from a COHIBA model file.

    * **`basedir`:** Path to folder with model_file.xml.
       Make sure that the folder has the same format as a COHIBA folder.
    * **`planned_wells_dir`:** Path to folder with planned well files.
       Make sure that all planned wells have format 'ROXAR RMS well'."""

    # pylint: disable=too-many-instance-attributes
    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        basedir: Path,
        planned_wells_dir: Path = None,
    ):

        super().__init__()
        self.plotly_theme = webviz_settings.theme.plotly_theme
        self.uid = uuid4()
        WEBVIZ_ASSETS.add(
            Path(webviz_subsurface.__file__).parent / "_assets" / "css" / "modal.css"
        )
        self.set_callbacks(app)

        self.basedir = basedir
        self.planned_wells_dir = planned_wells_dir
        self.modelfile_path = basedir / "model_file.xml"
        self.modelfile = get_path(self.modelfile_path)
        self.surfaces = load_surfaces(basedir, self.modelfile_path)
        self.planned_wellfiles = (
            json.load(find_files(planned_wells_dir, "*.txt"))
            if planned_wells_dir
            else None
        )
        self.wellfiles = json.load(find_files(basedir / "input" / "welldata", "*.txt"))
        self.wellfiles = [str(get_path(Path(w))) for w in self.wellfiles]
        self.allfiles = json.load(find_files(basedir))
        self.allfiles.append(self.modelfile_path)
        self.allfiles += self.planned_wellfiles
        self.planned_wellfiles = [
            str(get_path(Path(w))) for w in self.planned_wellfiles
        ]
        self.surface_attributes = {}
        for i, surface in enumerate(self.surfaces):
            self.surface_attributes[surface["name"]] = {
                "color": get_color(i),
                "order": i,
                "name": surface["name"],
                "topofzone": surface["topofzone"],
                "surface": surface["d_"],
                "surface_de": surface["de_"],
                "surface_dt": surface["dt_"],
                "surface_dr": surface["dr_"],
                "surface_dte": surface["dte_"],
            }

        self.surfacenames = [surface["name"] for surface in self.surfaces]
        # Log files
        zonation_status_file = get_zonation_status(basedir)
        well_points_file = get_well_points(basedir)
        zonelog_name = get_zonelog_name(self.modelfile)
        self.xsec = HuvXsection(
            self.surface_attributes,
            zonation_status_file,
            well_points_file,
            zonelog_name,
        )
        target_points_file = get_target_points(basedir)
        self.df_well_target_points = FilterTable(target_points_file, well_points_file)

        # Wellfiles and planned wells
        self.planned_wells = {}
        if planned_wells_dir is not None:
            self.planned_wells = {
                wf: xtgeo.well_from_file(wfile=wf) for wf in self.planned_wellfiles
            }

        self.wells = {wf: xtgeo.well_from_file(wfile=wf) for wf in self.wellfiles}

        # Store current layers
        self.state = {"switch": False}
        self.layers_state = []

    def ids(self, element: str) -> str:
        return f"{element}-id-{self.uid}"

    @property
    def surface_types(self) -> List[str]:
        return [
            "Depth",
            "Depth uncertainty",
            "Depth residual",
            "Depth residual uncertainty",
            "Depth trend",
            "Depth trend uncertainty",
        ]

    @property
    def cross_section_graph_layout(self) -> html.Div:
        return html.Div(
            children=[
                wcc.Graph(
                    id=self.ids("xsec-view"),
                )
            ]
        )

    @property
    def cross_section_widgets_layout(self) -> html.Div:
        return html.Div(
            children=[
                html.Div(
                    children=[
                        dbc.Button(
                            "Surface Settings",
                            id=self.ids("button-open-graph-settings"),
                            color="light",
                            className="mr-1",
                        ),
                        dbc.Modal(
                            children=[
                                dbc.ModalHeader("Surface Settings"),
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
                                            id=self.ids("all-surfaces-checkbox"),
                                            options=[{"label": "all", "value": "True"}],
                                            value=["True"],
                                            persistence=True,
                                            persistence_type="session",
                                        ),
                                        dcc.Checklist(
                                            id=self.ids("surfaces-checklist"),
                                            options=[
                                                {"label": name, "value": name}
                                                for name in self.surfacenames
                                            ],
                                            value=self.surfacenames,
                                            persistence=True,
                                            persistence_type="session",
                                        ),
                                        dcc.Checklist(
                                            id=self.ids("surfaces-de-checklist"),
                                            options=[
                                                {
                                                    "label": name + " SD",
                                                    "value": name,
                                                    "disabled": False,
                                                }
                                                for name in self.surfacenames
                                            ],
                                            value=self.surfacenames,
                                            persistence=True,
                                            persistence_type="session",
                                        ),
                                    ],
                                ),
                                dbc.ModalFooter(
                                    children=[
                                        dbc.Button(
                                            "Close",
                                            id=self.ids("button-close-graph-settings"),
                                            className="ml-auto",
                                        ),
                                        dbc.Button(
                                            "Apply changes",
                                            id=self.ids("button-apply-checklist"),
                                            className="ml-auto",
                                        ),
                                    ]
                                ),
                            ],
                            id=self.ids("modal-graph-settings"),
                            size="sm",
                            centered=True,
                            backdrop=False,
                            fade=False,
                        ),
                        dbc.Button(
                            "Well Settings", id=self.ids("button-open-well-settings")
                        ),
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
                                            id=self.ids("all-well-settings-checkbox"),
                                            options=[{"label": "all", "value": "True"}],
                                            value=["True"],
                                            persistence=True,
                                            persistence_type="session",
                                        ),
                                        dcc.Checklist(
                                            id=self.ids("well-settings-checklist"),
                                            options=[
                                                {
                                                    "label": "Zonelog",
                                                    "value": "zonelog",
                                                },
                                                {
                                                    "label": "Zonation points",
                                                    "value": "zonation_points",
                                                },
                                                {
                                                    "label": "Conditional points",
                                                    "value": "conditional_points",
                                                },
                                            ],
                                            value=[
                                                "zonelog",
                                                "zonation_points",
                                                "conditional_points",
                                            ],
                                            persistence=True,
                                            persistence_type="session",
                                        ),
                                    ],
                                ),
                                dbc.ModalFooter(
                                    children=[
                                        dbc.Button(
                                            "Close",
                                            id=self.ids("button-close-well-settings"),
                                            className="ml-auto",
                                        ),
                                        dbc.Button(
                                            "Apply",
                                            id=self.ids(
                                                "button-apply-well-settings-checklist"
                                            ),
                                            className="ml-auto",
                                        ),
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
                                        {
                                            "label": self.wells[wf].wellname,
                                            "value": str(wf),
                                        }
                                        for wf in self.wellfiles
                                    ]
                                    + [
                                        {
                                            "label": self.planned_wells[wf].wellname,
                                            "value": str(wf),
                                        }
                                        for wf in self.planned_wellfiles
                                    ],
                                    value=str(self.wellfiles[0]),
                                    clearable=False,
                                    disabled=False,
                                    persistence=True,
                                    persistence_type="session",
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
    def target_points_tab_layout(self) -> dash_table.DataTable:
        df = self.df_well_target_points.get_targetpoints_df()
        return dash_table.DataTable(
            id=self.ids("target-point-table"),
            columns=[{"name": i, "id": i} for i in df.columns],
            data=df.to_dict("records"),
            sort_action="native",
            filter_action="native",
        )

    @property
    def well_points_tab_layout(self) -> html.Div:
        return html.Div(
            [
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
                                    id=self.ids("columns-checklist"),
                                    options=[
                                        {"label": name, "value": column_name}
                                        for name, column_name in zip(
                                            self.df_well_target_points.get_wellpoints_df()
                                            .keys()
                                            .values,
                                            self.df_well_target_points.get_wellpoints_df()
                                            .keys()
                                            .values,
                                        )
                                    ],
                                    value=[
                                        "Surface",
                                        "Well",
                                        "TVD",
                                        "MD",
                                        "Outlier",
                                        "Deleted",
                                        "Residual",
                                    ],
                                    persistence=True,
                                    persistence_type="session",
                                ),
                            ],
                        ),
                        dbc.ModalFooter(
                            children=[
                                dbc.Button(
                                    "Close",
                                    id=self.ids("button-close-table-settings"),
                                    className="ml-auto",
                                ),
                                dbc.Button(
                                    "Apply",
                                    id=self.ids("button-apply-columnlist"),
                                    className="ml-auto",
                                ),
                            ]
                        ),
                    ],
                    id=self.ids("modal-table-settings"),
                    size="sm",
                    centered=True,
                    backdrop=False,
                    fade=False,
                ),
                html.Div(id=self.ids("well-points-table-container")),
            ]
        )

    @property
    def left_flexbox_layout(self) -> html.Div:
        return html.Div(
            children=[
                wcc.FlexBox(
                    children=[
                        dcc.RadioItems(
                            labelStyle={"display": "inline-block"},
                            options=[
                                {"label": "Map view", "value": "map-view"},
                                {"label": "Surface picks table", "value": "table-view"},
                            ],
                            id=self.ids("map-table-radioitems"),
                            value="map-view",
                            persistence=True,
                            persistence_type="session",
                        )
                    ],
                    style={"padding": "5px"},
                ),
                html.Div(
                    id=self.ids("hidden-div-map-view"), children=[self.map_view_layout]
                ),  # Hidden div to store polyline points when in table view
                html.Div(
                    id=self.ids("hidden-div-table-view"),
                    children=[self.table_view_layout],
                ),
            ]
        )

    @property
    def map_view_layout(self) -> html.Div:
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
                                        {"label": name, "value": name}
                                        for name in self.surfacenames
                                    ],
                                    value=self.surfacenames[0],
                                    clearable=False,
                                    persistence=True,
                                    persistence_type="session",
                                ),
                            ]
                        ),
                    ],
                ),
                html.Div(
                    style={
                        "marginTop": "0px",
                        "height": "800px",
                        "zIndex": -9999,
                    },
                    children=[
                        webviz_subsurface_components.LeafletMap(
                            id=self.ids("layered-map"),
                            layers=[],
                            unitScale={},
                            autoScaleMap=True,
                            minZoom=-19,
                            drawTools={
                                "drawMarker": False,
                                "drawPolygon": False,
                                "drawPolyline": True,
                                "position": "topright",
                            },
                            switch={
                                "value": False,
                                "disabled": False,
                                "label": "Hillshading",
                            },
                            mouseCoords={"position": "bottomright"},
                            colorBar={"position": "bottomright"},
                        ),
                    ],
                ),
            ]
        )

    @property
    def table_view_layout(self) -> html.Div:
        df = self.xsec.get_intersection_dataframe(self.wells[self.wellfiles[0]])
        return html.Div(
            children=[
                html.Label(
                    id=self.ids("surface-picks-label"),
                    style={
                        "font-weight": "bold",
                        "textAlign": "center",
                    },
                ),
                dash_table.DataTable(
                    id=self.ids("uncertainty-table"),
                    columns=[{"name": i, "id": i} for i in df.columns],
                    data=df.to_dict("records"),
                    sort_action="native",
                    filter_action="native",
                ),
            ],
            style={"marginTop": "0px"},
        )

    @property
    def layout(self) -> dcc.Tabs:
        return dcc.Tabs(
            children=[
                dcc.Tab(
                    label="Cross section & map view",
                    children=[
                        wcc.FlexBox(
                            id=self.ids("layout"),
                            children=[
                                html.Div(
                                    style={"flex": 1}, children=self.left_flexbox_layout
                                ),
                                html.Div(
                                    style={"flex": 1.5},
                                    children=self.cross_section_widgets_layout,
                                ),
                            ],
                        )
                    ],
                ),
                dcc.Tab(
                    label="Target Points",
                    children=[html.Div(children=self.target_points_tab_layout)],
                ),
                dcc.Tab(label="Well Points", children=[self.well_points_tab_layout]),
            ]
        )

    # pylint: disable=too-many-statements
    def set_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output(self.ids("layered-map"), "layers"),
            [
                Input(self.ids("map-dropdown"), "value"),
                Input(self.ids("layered-map"), "switch"),  # Toggle hillshading on/off
                Input(self.ids("well-dropdown"), "value"),  # Wellfile
            ],
        )
        def _render_map(surface_name, switch, wellfile):
            """Renders map view for one surface with de, dt, dte, dr, dre and depth
            Wells marked with circles, trajectory and hillshading toggle
            """

            surfaces = [
                self.surface_attributes[surface_name]["surface"],
                self.surface_attributes[surface_name]["surface_de"],
                self.surface_attributes[surface_name]["surface_dr"],
                self.surface_attributes[surface_name]["surface_dt"],
                self.surface_attributes[surface_name]["surface_dte"],
            ]
            well_layers = get_well_layers(
                self.wells,
                self.planned_wells,
                surface_name,
                surfaces[0],
                wellfile,
            )
            layers = []
            for i, surface in enumerate(surfaces):
                layers.append(
                    SurfaceLeafletModel(
                        surface,
                        name=self.surface_types[i],
                        apply_shading=switch["value"],
                        updatemode="add",
                    ).layer
                )
            layers.extend(well_layers)
            # Deletes old layers when switching surface in dropdown
            old_layers = self.layers_state
            self.layers_state = layers.copy()
            if old_layers is not None and len(old_layers) > 0:
                for layer in old_layers:
                    layer["action"] = "delete"
                old_layers.extend(layers)
                layers = old_layers
            return layers

        @app.callback(
            Output(self.ids("xsec-view"), "figure"),
            [
                Input(self.ids("button-apply-checklist"), "n_clicks"),
                Input(self.ids("button-apply-well-settings-checklist"), "n_clicks"),
                Input(self.ids("well-dropdown"), "value"),  # wellpath
                Input(self.ids("layered-map"), "polyline_points"),  # Polyline
            ],
            [
                State(self.ids("surfaces-checklist"), "value"),  # surfacefiles
                State(self.ids("surfaces-de-checklist"), "value"),  # surfacefiles keys
                State(self.ids("well-settings-checklist"), "value"),  # Well settings
            ],
        )
        def _render_xsection(
            n_apply_sfc,
            n_apply_well,
            wellfile,
            polyline,
            surfacefiles,
            de_keys,
            well_settings,
        ):
            """Renders cross section view from wellfile or polyline drawn in map view"""
            _ = n_apply_sfc, n_apply_well
            ctx = callback_context
            if wellfile in self.wellfiles:
                well = self.wells[wellfile]
                is_planned = False
            else:
                well = self.planned_wells[wellfile]
                is_planned = True
            well.create_relative_hlen()
            if (
                ctx.triggered[0]["prop_id"]
                == self.ids("layered-map") + ".polyline_points"
                and polyline is not None
            ):
                well = None
            self.xsec.set_de_and_surface_lines(surfacefiles, de_keys, well, polyline)
            self.xsec.set_xsec_fig(
                surfacefiles, de_keys, well_settings, well, is_planned=is_planned
            )
            return self.xsec.fig

        @app.callback(
            Output(self.ids("well-dropdown"), "value"),  # Wellfile
            [Input(self.ids("layered-map"), "clicked_shape")],  # Clicked circle on map
        )
        def _update_render_map_and_xsection(clicked_shape):
            """Updates well dropdown value when choosing a new circle"""
            return (
                clicked_shape["id"] if clicked_shape is not None else self.wellfiles[0]
            )

        @app.callback(
            Output(self.ids("surfaces-checklist"), "value"),
            [Input(self.ids("all-surfaces-checkbox"), "value")],
        )
        def _update_surface_tickboxes(all_surfaces_checkbox):
            """Toggle on/off all surfaces in graph settings modal"""
            return self.surfacenames if all_surfaces_checkbox == ["True"] else []

        @app.callback(
            Output(self.ids("modal-graph-settings"), "is_open"),
            [
                Input(self.ids("button-open-graph-settings"), "n_clicks"),
                Input(self.ids("button-close-graph-settings"), "n_clicks"),
                Input(self.ids("button-open-graph-settings"), "disabled"),
            ],
            [State(self.ids("modal-graph-settings"), "is_open")],
        )
        def _toggle_modal_graph_settings(n_open, n_close, disabled, is_open):
            """Open or close graph settings modal button"""
            if disabled:
                switch = False
            elif n_open or n_close:
                switch = not is_open
            else:
                switch = is_open
            return switch

        @app.callback(
            Output(self.ids("surfaces-de-checklist"), "options"),
            [Input(self.ids("surfaces-checklist"), "value")],
            [State(self.ids("surfaces-de-checklist"), "options")],
        )
        def _disable_error_checkboxes(surface_values, de_options):
            """Removes ability to toggle depth error when
            corresponding surface is disabled in graph settings modal
            """
            for i, opt in enumerate(de_options):
                if (surface_values is None) or (opt["value"] not in surface_values):
                    de_options[i]["disabled"] = True
                else:
                    de_options[i]["disabled"] = False
            return de_options

        @app.callback(
            Output(self.ids("well-settings-checklist"), "value"),
            [Input(self.ids("all-well-settings-checkbox"), "value")],
        )
        def _update_well_settings_tickboxes(all_well_attributes_checkbox):
            """Toggle on/off all options in well settings modal"""
            return (
                ["zonelog", "zonation_points", "conditional_points"]
                if all_well_attributes_checkbox == ["True"]
                else []
            )

        @app.callback(
            Output(self.ids("modal-well-settings"), "is_open"),
            [
                Input(self.ids("button-open-well-settings"), "n_clicks"),
                Input(self.ids("button-close-well-settings"), "n_clicks"),
            ],
            [State(self.ids("modal-well-settings"), "is_open")],
        )
        def _toggle_modal_well_settings(n_open, n_close, is_open):
            """Open or close well settings modal button"""
            if n_open or n_close:
                return not is_open
            return is_open

        @app.callback(
            Output(self.ids("well-points-table-container"), "children"),
            [
                Input(self.ids("button-apply-columnlist"), "n_clicks"),
            ],
            [
                State(self.ids("columns-checklist"), "value"),
            ],  # columns list
        )
        # pylint: disable=unused-argument
        def display_output(n_clicks, column_list):
            """Renders wellpoints table from csv file"""
            wellpoints_df = self.df_well_target_points.update_wellpoints_df(column_list)
            return html.Div(
                [
                    dash_table.DataTable(
                        id=self.ids("well-points-table"),
                        columns=[{"name": i, "id": i} for i in wellpoints_df.columns],
                        data=wellpoints_df.to_dict("records"),
                        sort_action="native",
                        filter_action="native",
                    ),
                ]
            )

        @app.callback(
            Output(self.ids("modal-table-settings"), "is_open"),
            [
                Input(self.ids("button-open-table-settings"), "n_clicks"),
                Input(self.ids("button-close-table-settings"), "n_clicks"),
            ],
            [State(self.ids("modal-table-settings"), "is_open")],
        )
        def _toggle_modal_table_settings(n_open, n_close, is_open):
            """Open or close table settings modal button"""
            if n_open or n_close:
                return not is_open
            return is_open

        @app.callback(
            [
                Output(self.ids("hidden-div-map-view"), "hidden"),
                Output(self.ids("hidden-div-table-view"), "hidden"),
            ],
            [Input(self.ids("map-table-radioitems"), "value")],
        )
        def _toggle_left_flexbox_content(value):
            """Returns which left flexbox content is visible/hidden"""
            if value == "table-view":
                switch = True, False
            else:
                switch = False, True
            return switch

        @app.callback(
            Output(self.ids("uncertainty-table"), "data"),
            [Input(self.ids("well-dropdown"), "value")],
        )
        def _render_uncertainty_table(wellfile):
            if wellfile in self.wellfiles:
                well = self.wells[wellfile]
            else:
                well = self.planned_wells[wellfile]
            df = self.xsec.get_intersection_dataframe(well)
            return df.to_dict("records")

        @app.callback(
            Output(self.ids("surface-picks-label"), "children"),
            [Input(self.ids("well-dropdown"), "value")],
        )
        def _render_surface_picks_label(wellfile):
            if wellfile in self.wellfiles:
                wellname = self.wells[wellfile].wellname
            else:
                wellname = self.planned_wells[wellfile].wellname
            return f"Surface picks for {wellname}"

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        functions = [(get_path, [{"path": Path(fn)}]) for fn in self.allfiles]
        functions.append((find_files, [{"folder": self.basedir}]))
        if self.planned_wells_dir is not None:
            functions.append(
                (
                    find_files,
                    [
                        {"folder": self.planned_wells_dir, "pattern": "*.txt"},
                        {
                            "folder": self.basedir / "input" / "welldata",
                            "pattern": "*.txt",
                        },
                    ],
                )
            )
        functions.append(
            (
                get_surfaces,
                [
                    {
                        "basedir": self.basedir,
                        "modelfile": self.modelfile_path,
                    }
                ],
            )
        )
        return functions


@webvizstore
def get_path(path) -> Path:
    return Path(path)


def get_color(i):
    """Create a list of colors for surface layers
    Args:
        i: Index of surface layer in surfacefiles list
    Returns:
        List of colors for surface layers
    """
    colors = [
        "rgb(70,130,180)",  # Steel blue
        "rgb(0,0,255)",  # Blue
        "rgb(173,255,47)",  # Green yellow
        "rgb(0,128,0)",  # Green
        "rgb(0,255,0)",  # Lime
        "rgb(60,179,113)",  # Medium sea green
        "rgb(255,105,180)",  # Pink
        "rgb(221,160,221)",  # Plum
        "rgb(255,255,0)",  # Yellow
        "rgb(244,164,96)",  # Tan
        "rgb(255,140,0)",  # Orange
        "rgb(255,69,0)",  # Blood orange
        "rgb(255,0,0)",  # Red
        "rgb(220,20,60)",  # Crimson
        "rgb(255,0,255)",  # Fuchsia
    ]
    n_colors = len(colors)
    return colors[(i) % (n_colors)]


def load_surfaces(basedir: Path, modelfile):
    surface_types = {
        "depth": "d_",
        "depth-trend": "dt_",
        "depth-error": "de_",
        "depth-trend-error": "dte_",
        "depth-residual": "dr_",
    }
    surface_data = json.load(get_surfaces(basedir, modelfile))
    for surface in surface_data:
        for stype in surface_types.values():
            surface[stype] = surface_from_json(surface[stype]) if stype else None
    return surface_data


@webvizstore
def get_surfaces(basedir: Path, modelfile) -> io.BytesIO:
    modelfile = ET.parse(get_path(modelfile)).getroot()
    surface_types = {
        "depth": "d_",
        "depth-trend": "dt_",
        "depth-error": "de_",
        "depth-trend-error": "dte_",
        "depth-residual": "dr_",
    }
    surface_wrappers = modelfile.findall(".//surface")
    surfaces = []
    for element in surface_wrappers:
        surface = {
            "name": element.findtext("name"),
            "topofzone": element.findtext("top-of-zone"),
        }
        for s_mtype, s_type in surface_types.items():
            surface[s_type] = (
                surface_to_json(
                    str(
                        basedir
                        / "output"
                        / "surfaces"
                        / f"{s_type}{surface['name']}.rxb"
                    )
                )
                if element.find("output").findtext(s_mtype) == "yes"
                else None
            )
        surfaces.append(surface)
    return io.BytesIO(json.dumps(surfaces).encode())


def surface_to_json(surfacepath: Path) -> str:
    surface = xtgeo.surface_from_file(str(surfacepath), fformat="irap_binary")
    return json.dumps(
        {
            "ncol": surface.ncol,
            "nrow": surface.nrow,
            "xori": surface.xori,
            "yori": surface.yori,
            "rotation": surface.rotation,
            "xinc": surface.xinc,
            "yinc": surface.yinc,
            "values": surface.values.copy().filled(np.nan).tolist(),
        }
    )


def surface_from_json(surfaceobj):
    data = json.loads(surfaceobj)
    surface = xtgeo.RegularSurface(**data)
    surface.values = np.array(data["values"])
    return surface


# TODO(Sigurd) Delete unused function?
# def extract_topofzone_names(modelfile):
#    modelfile = ET.parse(modelfile).getroot()
#    surface_wrappers = modelfile.findall(".//surface")
#    topofzone_names = []
#    for element in surface_wrappers:
#        name = element.findtext("top-of-zone")
#        topofzone_names.append(name)
#    return topofzone_names


# TODO(Sigurd) Delete unused function?
# def get_well_files(basedir: Path) -> io.BytesIO:
#    well_dir = os.path.join(basedir, "input", "welldata")
#    well_dir = basedir / "input" / "welldata"
#    well_files = []
#    try:
#        for file in os.listdir(well_dir):
#            if Path(file).suffix == ".txt":
#                well_files.append(os.path.join(well_dir, file))
#    except FileNotFoundError:
#        pass
#    well_files.sort()
#    return io.BytesIO(json.dumps(well_files).encode())


def get_target_points(basedir: Path) -> Path:
    return get_path(basedir / "output" / "log_files" / "targetpoints.csv")


def get_well_points(basedir: Path) -> Path:
    return get_path(basedir / "output" / "log_files" / "wellpoints.csv")


def get_zonelog_name(modelfile):
    modelfile = ET.parse(modelfile).getroot()
    zonelog_wrapper = modelfile.findtext(".//zone-log-name")
    return zonelog_wrapper


def get_zonation_status(basedir: Path) -> Path:
    return get_path(basedir / "output" / "log_files" / "zonation_status.csv")


# TODO(Sigurd) Delete unused?
# @webvizstore
# def get_surface_files(basedir: Path, surface_names, surface_type) -> io.BytesIO:
#    surface_dir = basedir / "output" / "surfaces"
#    surface_files = [
#        surface_dir / f"{surface_type}{surface_name}.rxb"
#        for surface_name in surface_names
#    ]
#    for path in surface_files:
#        if not path.is_file():
#            surface_files = None
#    if surface_files is not None:
#        surface_files = [str(surf) for surf in surface_files]
#    return io.BytesIO(json.dumps(surface_files).encode())


@webvizstore
def find_files(folder: Path, pattern: str = "*") -> io.BytesIO:
    return io.BytesIO(
        json.dumps(
            sorted(
                [
                    str(filename)
                    for filename in folder.glob(f"**/{pattern}")
                    if filename.is_file()
                ]
            )
        ).encode()
    )
