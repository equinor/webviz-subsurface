import json
from uuid import uuid4
from pathlib import Path
from typing import List

import dash
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_config import WebvizPluginABC
from webviz_config.webviz_store import webvizstore
from webviz_config.utils import calculate_slider_step

from .._datainput.seismic import load_cube_data, get_iline, get_xline, get_zslice


class SegyViewer(WebvizPluginABC):
    """### SegyViewer

Inspired by [SegyViewer for Python](https://github.com/equinor/segyviewer) this plugin
visualizes seismic 3D cubes with 3 plots (inline, crossline and zslice).
The plots are linked and updates are done by clicking in the plots.

* `segyfiles`: List of file paths to segyfiles
* `zunit`: z-unit for display
* `colors`: List of colors to use
"""

    def __init__(
        self, app, segyfiles: List[Path], zunit="depth (m)", colors: list = None
    ):

        super().__init__()

        self.zunit = zunit
        self.segyfiles = [str(segy) for segy in segyfiles]
        self.initial_colors = (
            colors
            if colors
            else [
                "#67001f",
                "#ab152a",
                "#d05546",
                "#ec9372",
                "#fac8ac",
                "#faeae1",
                "#e6eff4",
                "#bbd9e9",
                "#7db7d6",
                "#3a8bbf",
                "#1f61a5",
                "#053061",
            ]
        )
        self.init_state = self.update_state(self.segyfiles[0])
        self.init_state.get("colorscale", self.initial_colors)
        self.init_state.get("uirevision", str(uuid4()))
        self.uid = uuid4()
        self.plotly_theme = app.webviz_settings["theme"].plotly_theme
        self.set_callbacks(app)

    def ids(self, element):
        """Generate unique id for dom element"""
        return f"{element}-id-{self.uid}"

    def update_state(self, cubepath, **kwargs):
        cube = load_cube_data(get_path(cubepath))
        state = {
            "cubepath": cubepath,
            "iline": int(cube.ilines[int(len(cube.ilines) / 2)]),
            "xline": int(cube.xlines[int(len(cube.xlines) / 2)]),
            "zslice": float(cube.zslices[int(len(cube.zslices) / 2)]),
            "min_value": float(f"{round(cube.values.min(), 2):2f}"),
            "max_value": float(f"{round(cube.values.max(), 2):2f}"),
            "color_min_value": float(f"{round(cube.values.min(), 2):2f}"),
            "color_max_value": float(f"{round(cube.values.max(), 2):2f}"),
            "uirevision": str(uuid4()),
            "colorscale": self.initial_colors,
        }
        if kwargs:
            for key, value in kwargs.items():
                state[key] = value
        return state

    @property
    def tour_steps(self):
        return [
            {
                "id": self.ids("layout"),
                "content": (
                    "Visualizes SEG-Y cubes. Display different slices "
                    "of the cube by clicking (MB1) in the different plots. "
                    "To zoom, hold MB1 and draw a vertical/horizontal "
                    "line or a rectangle."
                ),
            },
            {
                "id": self.ids("cube"),
                "content": "The currently visualized seismic cube.",
            },
            {
                "id": self.ids("inline"),
                "content": "Selected inline for the seismic cube.",
            },
            {
                "id": self.ids("xline"),
                "content": "Selected crossline for the seismic cube.",
            },
            {
                "id": self.ids("zslice"),
                "content": "Selected zslice for the seismic cube.",
            },
            {
                "id": self.ids("color-scale"),
                "content": "Click this button to change colorscale",
            },
            {
                "id": self.ids("color-values"),
                "content": "Drag either node of slider to truncate color ranges.",
            },
            {
                "id": self.ids("color-reset"),
                "content": (
                    "Click this button to update color slider min/max and reset ranges."
                ),
            },
            {
                "id": self.ids("zoom"),
                "content": "Click this button to reset zoom/pan state in the plot.",
            },
        ]

    @property
    def settings_layout(self):
        """Layout for color and other settings"""
        return wcc.FlexBox(
            style={"margin": "50px"},
            children=[
                html.Div(
                    style={"width": "100%"},
                    children=html.Label(
                        children=[
                            html.Span("Seismic cube:", style={"font-weight": "bold"}),
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
                ),
                html.Div(
                    style={"marginRight": "50px", "width": "50%", "marginLeft": "50px"},
                    children=[
                        html.Label(
                            style={"font-weight": "bold", "textAlign": "center"},
                            children="Set colorscale",
                        ),
                        wcc.ColorScales(
                            id=self.ids("color-scale"),
                            colorscale=self.initial_colors,
                            nSwatches=12,
                        ),
                    ],
                ),
                html.Div(
                    style={"marginRight": "50px", "width": "50%", "marginLeft": "50px"},
                    children=[
                        html.P(
                            "Color range",
                            style={"textAlign": "center", "font-weight": "bold"},
                        ),
                        dcc.RangeSlider(
                            id=self.ids("color-values"),
                            min=self.init_state["min_value"],
                            max=self.init_state["max_value"],
                            value=[
                                self.init_state["min_value"],
                                self.init_state["max_value"],
                            ],
                            tooltip={"always_visible": True},
                            step=calculate_slider_step(
                                min_value=self.init_state["min_value"],
                                max_value=self.init_state["max_value"],
                                steps=100,
                            ),
                        ),
                    ],
                ),
                html.Button(id=self.ids("color-reset"), children="Reset Range"),
                html.Button(id=self.ids("zoom"), children="Reset zoom"),
            ],
        )

    @property
    def layout(self):
        return html.Div(
            id=self.ids("layout"),
            children=wcc.FlexBox(
                children=[
                    html.Div(
                        style={"width": "50%"},
                        children=[
                            html.Div(
                                style={"minWidth": "200px", "height": "400px"},
                                children=wcc.Graph(
                                    config={"displayModeBar": False},
                                    id=self.ids("inline"),
                                ),
                            ),
                            html.Div(
                                style={"minWidth": "200px", "height": "400px"},
                                children=wcc.Graph(
                                    config={"displayModeBar": False},
                                    id=self.ids("xline"),
                                ),
                            ),
                        ],
                    ),
                    html.Div(
                        style={"width": "50%"},
                        children=[
                            html.Div(
                                style={"minWidth": "200px", "height": "400px"},
                                children=wcc.Graph(
                                    config={"displayModeBar": False},
                                    id=self.ids("zslice"),
                                ),
                            ),
                            self.settings_layout,
                        ],
                    ),
                    dcc.Store(
                        id=self.ids("state-storage"), data=json.dumps(self.init_state)
                    ),
                ]
            ),
        )

    # pylint: disable=too-many-statements
    def set_callbacks(self, app):
        @app.callback(
            Output(self.ids("state-storage"), "data"),
            [
                Input(self.ids("cube"), "value"),
                Input(self.ids("inline"), "clickData"),
                Input(self.ids("xline"), "clickData"),
                Input(self.ids("zslice"), "clickData"),
                Input(self.ids("color-values"), "value"),
                Input(self.ids("color-scale"), "colorscale"),
                Input(self.ids("zoom"), "n_clicks"),
                Input(self.ids("color-reset"), "n_clicks"),
            ],
            [
                State(self.ids("zslice"), "figure"),
                State(self.ids("state-storage"), "data"),
            ],
        )
        # pylint: disable=unused-argument,too-many-arguments
        def _update_state(
            cubepath,
            icd,
            xcd,
            zcd,
            color_values,
            colorscale,
            zoom_btn,
            reset_range_btn,
            zfig,
            store,
        ):
            """Updates dcc.Store object with active iline, xline, zlayer and color settings.
            """
            store = json.loads(store)
            ctx = dash.callback_context.triggered[0]["prop_id"]
            x_was_clicked = (
                xcd if xcd and ctx == f"{self.ids('xline')}.clickData" else None
            )
            i_was_clicked = (
                icd if icd and ctx == f"{self.ids('inline')}.clickData" else None
            )
            z_was_clicked = (
                zcd if zcd and ctx == f"{self.ids('zslice')}.clickData" else None
            )
            if ctx == f"{self.ids('cube')}.value":
                store = self.update_state(cubepath)
            if ctx == f"{self.ids('zoom')}.n_clicks":
                store["uirevision"] = str(uuid4())
            if x_was_clicked:
                store["iline"] = xcd["points"][0]["x"]
                store["zslice"] = xcd["points"][0]["y"]
            if z_was_clicked:
                store["iline"] = zcd["points"][0]["x"]
                store["xline"] = zcd["points"][0]["y"]
                store["zslice"] = float(zfig["data"][0]["text"])
            if i_was_clicked:
                store["xline"] = icd["points"][0]["x"]
                store["zslice"] = icd["points"][0]["y"]
            if ctx == f"{self.ids('color-reset')}.n_clicks":
                store["color_min_value"] = store["min_value"]
                store["color_max_value"] = store["max_value"]
            else:
                store["color_min_value"] = color_values[0]
                store["color_max_value"] = color_values[1]
            store["colorscale"] = colorscale
            return json.dumps(store)

        @app.callback(
            Output(self.ids("zslice"), "figure"),
            [Input(self.ids("state-storage"), "data")],
        )
        def _set_zslice(state):
            """Updates z-slice heatmap"""
            if not state:
                raise PreventUpdate
            state = json.loads(state)
            cube = load_cube_data(str(get_path(state["cubepath"])))
            shapes = [
                {
                    "type": "line",
                    "x0": state["iline"],
                    "y0": cube.xlines[0],
                    "x1": state["iline"],
                    "y1": cube.xlines[-1],
                    "line": {"width": 1, "dash": "dot"},
                },
                {
                    "type": "line",
                    "y0": state["xline"],
                    "x0": cube.ilines[0],
                    "y1": state["xline"],
                    "x1": cube.ilines[-1],
                    "line": {"width": 1, "dash": "dot"},
                },
            ]

            zslice_arr = get_zslice(cube, state["zslice"])

            fig = make_heatmap(
                zslice_arr,
                self.plotly_theme,
                showscale=True,
                text=str(state["zslice"]),
                title=f'Zslice {state["zslice"]} ({self.zunit})',
                xaxis_title="Inline",
                yaxis_title="Crossline",
                reverse_y=False,
                zmin=state["color_min_value"],
                zmax=state["color_max_value"],
                colorscale=state["colorscale"],
                uirevision=state["uirevision"],
            )
            fig["layout"]["shapes"] = shapes
            fig["layout"]["xaxis"].update({"constrain": "domain"})
            fig["layout"]["yaxis"].update({"scaleanchor": "x"})
            return fig

        @app.callback(
            Output(self.ids("inline"), "figure"),
            [Input(self.ids("state-storage"), "data")],
        )
        def _set_iline(state):
            """Updates inline heatmap"""
            if not state:
                raise PreventUpdate
            state = json.loads(state)
            cube = load_cube_data(str(get_path(state["cubepath"])))
            shapes = [
                {
                    "type": "line",
                    "x0": state["xline"],
                    "y0": cube.zslices[0],
                    "x1": state["xline"],
                    "y1": cube.zslices[-1],
                    "line": {"width": 1, "dash": "dot"},
                },
                {
                    "type": "line",
                    "x0": cube.xlines[0],
                    "y0": state["zslice"],
                    "x1": cube.xlines[-1],
                    "y1": state["zslice"],
                    "line": {"width": 1, "dash": "dot"},
                },
            ]
            iline_arr = get_iline(cube, state["iline"])

            fig = make_heatmap(
                iline_arr,
                self.plotly_theme,
                xaxis=cube.xlines,
                yaxis=cube.zslices,
                title=f'Inline {state["iline"]}',
                xaxis_title="Crossline",
                yaxis_title=self.zunit,
                zmin=state["color_min_value"],
                zmax=state["color_max_value"],
                colorscale=state["colorscale"],
                uirevision=state["uirevision"],
            )
            fig["layout"]["shapes"] = shapes
            return fig

        @app.callback(
            Output(self.ids("xline"), "figure"),
            [Input(self.ids("state-storage"), "data")],
        )
        def _set_xline(state):
            """Update xline heatmap"""
            if not state:
                raise PreventUpdate
            state = json.loads(state)
            cube = load_cube_data(str(get_path(state["cubepath"])))
            shapes = [
                {
                    "type": "line",
                    "x0": state["iline"],
                    "y0": cube.zslices[0],
                    "x1": state["iline"],
                    "y1": cube.zslices[-1],
                    "line": {"width": 1, "dash": "dot"},
                },
                {
                    "type": "line",
                    "x0": cube.ilines[0],
                    "y0": state["zslice"],
                    "x1": cube.ilines[-1],
                    "y1": state["zslice"],
                    "line": {"width": 1, "dash": "dot"},
                },
            ]
            xline_arr = get_xline(cube, state["xline"])
            fig = make_heatmap(
                xline_arr,
                self.plotly_theme,
                xaxis=cube.ilines,
                yaxis=cube.zslices,
                title=f'Crossline {state["xline"]}',
                xaxis_title="Inline",
                yaxis_title=self.zunit,
                zmin=state["color_min_value"],
                zmax=state["color_max_value"],
                colorscale=state["colorscale"],
                uirevision=state["uirevision"],
            )
            fig["layout"]["shapes"] = shapes
            return fig

        @app.callback(
            [
                Output(self.ids("color-values"), "min"),
                Output(self.ids("color-values"), "max"),
                Output(self.ids("color-values"), "value"),
                Output(self.ids("color-values"), "step"),
            ],
            [Input(self.ids("color-reset"), "n_clicks")],
            [State(self.ids("state-storage"), "data")],
        )
        # pylint: disable=unused-argument
        def _reset_color_range(btn_clicked, state):
            if not state:
                raise PreventUpdate
            state = json.loads(state)
            minv = state["min_value"]
            maxv = state["max_value"]
            value = [minv, maxv]
            step = calculate_slider_step(min_value=minv, max_value=maxv, steps=100)
            return minv, maxv, value, step

    @staticmethod
    def set_grid_layout(columns):
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
        }

    def add_webvizstore(self):
        return [(get_path, [{"path": fn}]) for fn in self.segyfiles]


# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
def make_heatmap(
    arr,
    theme,
    height=400,
    zmin=None,
    zmax=None,
    colorscale=None,
    uirevision=None,
    showscale=False,
    reverse_y=True,
    xaxis=None,
    yaxis=None,
    text=None,
    title=None,
    yaxis_title=None,
    xaxis_title=None,
):
    """Createst heatmap plot"""
    colors = (
        [[i / (len(colorscale) - 1), color] for i, color in enumerate(colorscale)]
        if colorscale
        else "RdBu"
    )
    layout = {}
    layout.update(theme["layout"])
    layout.update(
        {
            "height": height,
            "title": title,
            "uirevision": uirevision,
            "margin": {"b": 50, "t": 50, "r": 0},
            "yaxis": {
                "title": yaxis_title,
                "autorange": "reversed" if reverse_y else None,
            },
            "xaxis": {"title": xaxis_title},
        }
    )

    return {
        "data": [
            {
                "type": "heatmap",
                "text": text if text else None,
                "z": arr.tolist(),
                "x": xaxis,
                "y": yaxis,
                "zsmooth": "best",
                "showscale": showscale,
                "colorscale": colors,
                "zmin": zmin,
                "zmax": zmax,
            }
        ],
        "layout": layout,
    }


@webvizstore
def get_path(path) -> Path:
    return Path(path)
