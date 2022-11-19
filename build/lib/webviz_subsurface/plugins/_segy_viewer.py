import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple, Union
from uuid import uuid4

import numpy as np
import webviz_core_components as wcc
from dash import Dash, Input, Output, State, callback_context, dcc, html
from dash.exceptions import PreventUpdate
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.utils import calculate_slider_step
from webviz_config.webviz_store import webvizstore

from .._datainput.seismic import get_iline, get_xline, get_zslice, load_cube_data


class SegyViewer(WebvizPluginABC):
    """Inspired by [SegyViewer for Python](https://github.com/equinor/segyviewer) this plugin
visualizes seismic 3D cubes with 3 plots (inline, crossline and zslice).
The plots are linked and updates are done by clicking in the plots.

---

* **`segyfiles`:** List of file paths to `SEGY` files (absolute or relative to config file).
* **`zunit`:** z-unit for display.
* **`colors`:** List of hex colors use. \
Note that apostrophies should be used to avoid that hex colors are read as comments. E.g. \
`'#000000'` for black.

---

* [Examples of segyfiles](https://github.com/equinor/webviz-subsurface-testdata/tree/master/\
observed_data/seismic).

The segyfiles are on a `SEG-Y` format and can be investigated outside `webviz` using \
e.g. [xtgeo](https://xtgeo.readthedocs.io/en/latest/).

"""

    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        segyfiles: List[Path],
        zunit: str = "depth (m)",
        colors: list = None,
    ):

        super().__init__()

        self.zunit = zunit
        self.segyfiles: List[str] = [str(segy) for segy in segyfiles]
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

        self.plotly_theme = webviz_settings.theme.plotly_theme
        self.set_callbacks(app)

    def update_state(self, cubepath: str, **kwargs: Any) -> Dict[str, Any]:
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
    def tour_steps(self) -> List[dict]:
        return [
            {
                "id": self.uuid("layout"),
                "content": (
                    "Visualizes SEG-Y cubes. Display different slices "
                    "of the cube by clicking (MB1) in the different plots. "
                    "To zoom, hold MB1 and draw a vertical/horizontal "
                    "line or a rectangle."
                ),
            },
            {
                "id": self.uuid("cube"),
                "content": "The currently visualized seismic cube.",
            },
            {
                "id": self.uuid("inline"),
                "content": "Selected inline for the seismic cube.",
            },
            {
                "id": self.uuid("xline"),
                "content": "Selected crossline for the seismic cube.",
            },
            {
                "id": self.uuid("zslice"),
                "content": "Selected zslice for the seismic cube.",
            },
            {
                "id": self.uuid("color-scale"),
                "content": "Click this button to change colorscale",
            },
            {
                "id": self.uuid("color-values"),
                "content": "Drag either node of slider to truncate color ranges.",
            },
            {
                "id": self.uuid("color-reset"),
                "content": (
                    "Click this button to update color slider min/max and reset ranges."
                ),
            },
            {
                "id": self.uuid("zoom"),
                "content": "Click this button to reset zoom/pan state in the plot.",
            },
        ]

    @property
    def settings_layout(self) -> wcc.FlexBox:
        """Layout for color and other settings"""
        return wcc.Frame(
            style={"width": "40%"},
            children=[
                html.Div(
                    style={"width": "100%"},
                    children=wcc.Dropdown(
                        label="Seismic cube",
                        id=self.uuid("cube"),
                        options=[
                            {"label": Path(cube).stem, "value": cube}
                            for cube in self.segyfiles
                        ],
                        value=self.segyfiles[0],
                        clearable=False,
                    ),
                ),
                html.Div(
                    children=[
                        wcc.Label(
                            children="Set colorscale",
                        ),
                        wcc.ColorScales(
                            id=self.uuid("color-scale"),
                            colorscale=self.initial_colors,
                            nSwatches=12,
                        ),
                    ],
                ),
                html.Div(
                    children=[
                        wcc.RangeSlider(
                            label="Color range",
                            id=self.uuid("color-values"),
                            min=self.init_state["min_value"],
                            max=self.init_state["max_value"],
                            value=[
                                self.init_state["min_value"],
                                self.init_state["max_value"],
                            ],
                            tooltip={"placement": "bottom"},
                            step=calculate_slider_step(
                                min_value=self.init_state["min_value"],
                                max_value=self.init_state["max_value"],
                                steps=100,
                            ),
                        ),
                    ],
                ),
                html.Button(id=self.uuid("color-reset"), children="Reset Range"),
                html.Button(id=self.uuid("zoom"), children="Reset zoom"),
            ],
        )

    @property
    def layout(self) -> html.Div:
        return html.Div(
            id=self.uuid("layout"),
            children=wcc.FlexBox(
                children=[
                    wcc.FlexColumn(
                        children=[
                            wcc.Frame(
                                color="white",
                                style={"minWidth": "200px", "height": "400px"},
                                children=wcc.Graph(
                                    config={"displayModeBar": False},
                                    id=self.uuid("inline"),
                                ),
                            ),
                            wcc.Frame(
                                color="white",
                                style={"minWidth": "200px", "height": "400px"},
                                children=wcc.Graph(
                                    config={"displayModeBar": False},
                                    id=self.uuid("xline"),
                                ),
                            ),
                        ],
                    ),
                    wcc.FlexColumn(
                        children=[
                            wcc.Frame(
                                color="white",
                                style={"minWidth": "200px", "height": "400px"},
                                children=wcc.Graph(
                                    config={"displayModeBar": False},
                                    id=self.uuid("zslice"),
                                ),
                            ),
                            html.Div(
                                style={"height": "400px"}, children=self.settings_layout
                            ),
                        ],
                    ),
                    dcc.Store(
                        id=self.uuid("state-storage"),
                        storage_type="session",
                        data=json.dumps(self.init_state),
                    ),
                ]
            ),
        )

    # pylint: disable=too-many-statements
    def set_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output(self.uuid("state-storage"), "data"),
            [
                Input(self.uuid("cube"), "value"),
                Input(self.uuid("inline"), "clickData"),
                Input(self.uuid("xline"), "clickData"),
                Input(self.uuid("zslice"), "clickData"),
                Input(self.uuid("color-values"), "value"),
                Input(self.uuid("color-scale"), "colorscale"),
                Input(self.uuid("zoom"), "n_clicks"),
                Input(self.uuid("color-reset"), "n_clicks"),
            ],
            [
                State(self.uuid("zslice"), "figure"),
                State(self.uuid("state-storage"), "data"),
            ],
        )
        def _update_state(
            cubepath: str,
            icd: Union[dict, None],
            xcd: Union[dict, None],
            zcd: Union[dict, None],
            color_values: List[float],
            colorscale: List[float],
            _zoom_btn: Union[int, None],
            _reset_range_btn: Union[int, None],
            zfig: Union[dict, None],
            state_data_str: str,
        ) -> str:
            """Updates dcc.Store object with active iline, xline, zlayer and color settings."""

            store: dict = json.loads(state_data_str)
            ctx = callback_context.triggered[0]["prop_id"]
            x_was_clicked = (
                xcd if xcd and ctx == f"{self.uuid('xline')}.clickData" else None
            )
            i_was_clicked = (
                icd if icd and ctx == f"{self.uuid('inline')}.clickData" else None
            )
            z_was_clicked = (
                zcd if zcd and ctx == f"{self.uuid('zslice')}.clickData" else None
            )
            if ctx == f"{self.uuid('cube')}.value":
                store = self.update_state(cubepath)
            if ctx == f"{self.uuid('zoom')}.n_clicks":
                store["uirevision"] = str(uuid4())
            if x_was_clicked and xcd is not None:
                store["iline"] = xcd["points"][0]["x"]
                store["zslice"] = xcd["points"][0]["y"]
            if z_was_clicked and zcd is not None and zfig is not None:
                store["iline"] = zcd["points"][0]["x"]
                store["xline"] = zcd["points"][0]["y"]
                store["zslice"] = float(zfig["data"][0]["text"])
            if i_was_clicked and icd is not None:
                store["xline"] = icd["points"][0]["x"]
                store["zslice"] = icd["points"][0]["y"]
            if ctx == f"{self.uuid('color-reset')}.n_clicks":
                store["color_min_value"] = store["min_value"]
                store["color_max_value"] = store["max_value"]
            else:
                store["color_min_value"] = color_values[0]
                store["color_max_value"] = color_values[1]
            store["colorscale"] = colorscale
            return json.dumps(store)

        @app.callback(
            Output(self.uuid("zslice"), "figure"),
            [Input(self.uuid("state-storage"), "data")],
        )
        def _set_zslice(state_data_str: Union[str, None]) -> dict:
            """Updates z-slice heatmap"""
            if not state_data_str:
                raise PreventUpdate
            state = json.loads(state_data_str)
            cube = load_cube_data(get_path(state["cubepath"]))
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
                xaxis=cube.ilines,
                yaxis=cube.xlines,
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
            Output(self.uuid("inline"), "figure"),
            [Input(self.uuid("state-storage"), "data")],
        )
        def _set_iline(state_data_str: Union[str, None]) -> dict:
            """Updates inline heatmap"""
            if not state_data_str:
                raise PreventUpdate
            state = json.loads(state_data_str)
            cube = load_cube_data(get_path(state["cubepath"]))
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
            Output(self.uuid("xline"), "figure"),
            [Input(self.uuid("state-storage"), "data")],
        )
        def _set_xline(state_data_str: Union[str, None]) -> dict:
            """Update xline heatmap"""
            if not state_data_str:
                raise PreventUpdate
            state = json.loads(state_data_str)
            cube = load_cube_data(get_path(state["cubepath"]))
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
                Output(self.uuid("color-values"), "min"),
                Output(self.uuid("color-values"), "max"),
                Output(self.uuid("color-values"), "value"),
                Output(self.uuid("color-values"), "step"),
            ],
            [Input(self.uuid("color-reset"), "n_clicks")],
            [State(self.uuid("state-storage"), "data")],
        )
        def _reset_color_range(
            _btn_clicked: int, state_data_str: Union[str, None]
        ) -> Tuple[float, float, list, float]:
            if not state_data_str:
                raise PreventUpdate
            state = json.loads(state_data_str)
            minv = state["min_value"]
            maxv = state["max_value"]
            value = [minv, maxv]
            step = calculate_slider_step(min_value=minv, max_value=maxv, steps=100)
            return minv, maxv, value, step

    @staticmethod
    def set_grid_layout(columns: str) -> dict:
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
        }

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        return [(get_path, [{"path": fn}]) for fn in self.segyfiles]


# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
def make_heatmap(
    arr: np.ndarray,
    theme: dict,
    height: int = 400,
    zmin: float = None,
    zmax: float = None,
    colorscale: list = None,
    uirevision: str = None,
    showscale: bool = False,
    reverse_y: bool = True,
    xaxis: np.ndarray = None,
    yaxis: np.ndarray = None,
    text: str = None,
    title: str = None,
    yaxis_title: str = None,
    xaxis_title: str = None,
) -> Dict[str, Any]:
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
def get_path(path: str) -> Path:
    return Path(path)
