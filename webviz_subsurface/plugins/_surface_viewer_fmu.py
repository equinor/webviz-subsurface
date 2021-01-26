from typing import List, Union, Tuple, Callable
from pathlib import Path
import json
import io
import warnings

import numpy as np
import pandas as pd
import xtgeo
import dash
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_html_components as html
import dash_core_components as dcc
from webviz_subsurface_components import LeafletMap
import webviz_core_components as wcc
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE
from webviz_config import WebvizPluginABC
from webviz_config import WebvizSettings

from webviz_subsurface._datainput.fmu_input import get_realizations, find_surfaces
from webviz_subsurface._datainput.surface import load_surface
from webviz_subsurface._datainput.well import make_well_layers
from webviz_subsurface._private_plugins.surface_selector import SurfaceSelector
from webviz_subsurface._models import SurfaceLeafletModel


class SurfaceViewerFMU(WebvizPluginABC):
    """Covisualize surfaces from an ensemble.

There are 3 separate map views. 2 views can be set independently, while
the 3rd view displays the resulting map by combining the other maps, e.g.
by taking the difference or summing the values.

There is flexibility in which combinations of surfaces that are displayed
and calculated, such that surfaces can be compared across ensembles and realizations.

Statistical calculations across the ensemble(s) are
done on the fly. If the ensemble(s) or surfaces have a large size, it is recommended
to run webviz in `portable` mode so that the statistical surfaces are pre-calculated,
and available for instant viewing.

---

* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`attributes`:** List of surface attributes to include, if not given
    all surface attributes will be included.
* **`attribute_settings`:** Dictionary with setting for each attribute.
    Available settings are:
    * `min`: Truncate colorscale (lower limit).
    * `max`: Truncate colorscale (upper limit).
    * `color`: List of hexadecimal colors.
    * `unit`: Text to display as unit in label.
* **`wellfolder`:** Folder with RMS wells.
* **`wellsuffix`:** File suffix for wells in well folder.
* **`map_height`:** Set the height in pixels for the map views.

---
The available maps are gathered from the `share/results/maps/` folder
for each realization. Subfolders are not supported.

The filenames need to follow a fairly strict convention, as the filenames are used as metadata:
`horizon_name--attribute--date` (`--date` is optional). The files should be on `irap binary`
format with the suffix `.gri`. The date is of the form `YYYYMMDD` or
`YYYYMMDD_YYYYMMDD`, the latter would be for a delta surface between two dates.
See [this folder]\
(https://github.com/equinor/webviz-subsurface-testdata/tree/master/reek_history_match/\
realization-0/iter-0/share/results/maps) \
for examples of file naming conventions.

The `attribute_settings` consists of optional settings for the individual attributes that are
extracted based on the filenames mentioned above. For attributes called `atr_a` and `atr_b`, the
configuration of `attribute_settings` could e.g. be:
```yaml
attribute_settings:
  atr_a:
    min: 4
    max: 10
    unit: m
  atr_b:
    color:
    - "#000004"
    - "#1b0c41"
    - "#4a0c6b"
    - "#781c6d"
```

"""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        app: dash.Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        attributes: list = None,
        attribute_settings: dict = None,
        wellfolder: Path = None,
        wellsuffix: str = ".w",
        map_height: int = 600,
    ):

        super().__init__()
        self.ens_paths = {
            ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
            for ens in ensembles
        }

        # Find surfaces
        self.surfacedf = find_surfaces(self.ens_paths)
        if attributes is not None:
            self.surfacedf = self.surfacedf[
                self.surfacedf["attribute"].isin(attributes)
            ]
            if self.surfacedf.empty:
                raise ValueError("No surfaces found with the given attributes")
        self.attribute_settings: dict = attribute_settings if attribute_settings else {}
        self.map_height = map_height
        self.surfaceconfig = surfacedf_to_dict(self.surfacedf)
        self.wellfolder = wellfolder
        self.wellsuffix = wellsuffix
        self.wellfiles: Union[List[str], None] = (
            json.load(find_files(wellfolder, wellsuffix))
            if wellfolder is not None
            else None
        )
        self.well_layer = (
            make_well_layers([get_path(wellfile) for wellfile in self.wellfiles])
            if self.wellfiles
            else None
        )
        # Extract realizations and sensitivity information
        self.ens_df = get_realizations(
            ensemble_paths=self.ens_paths, ensemble_set_name="EnsembleSet"
        )
        self.selector = SurfaceSelector(app, self.surfaceconfig, ensembles)
        self.selector2 = SurfaceSelector(app, self.surfaceconfig, ensembles)

        self.set_callbacks(app)

    @property
    def ensembles(self) -> List[str]:
        return list(self.ens_df["ENSEMBLE"].unique())

    def realizations(
        self, ensemble: str, sensname: str = None, senstype: str = None
    ) -> List[str]:
        df = self.ens_df.loc[self.ens_df["ENSEMBLE"] == ensemble].copy()
        if sensname and senstype:
            df = df.loc[(df["SENSNAME"] == sensname) & (df["SENSCASE"] == senstype)]
        return list(df["REAL"]) + ["Mean", "StdDev", "Min", "Max"]

    @property
    def tour_steps(self) -> List[dict]:
        return [
            {
                "id": self.uuid("layout"),
                "content": (
                    "Dashboard to compare surfaces from a FMU ensemble. "
                    "The two left views can be set independently, while the right "
                    "view shows a calculated surface."
                ),
            },
            {
                "id": self.uuid("settings-view1"),
                "content": ("Settings for the first map view"),
            },
            {
                "id": self.uuid("settings-view2"),
                "content": ("Settings for the second map view"),
            },
            {
                "id": self.uuid("settings-view3"),
                "content": ("Settings for the calculated map view"),
            },
        ]

    @staticmethod
    def set_grid_layout(columns: str) -> dict:
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
        }

    def ensemble_layout(
        self,
        ensemble_id: str,
        ens_prev_id: str,
        ens_next_id: str,
        real_id: str,
        real_prev_id: str,
        real_next_id: str,
    ) -> wcc.FlexBox:
        return wcc.FlexBox(
            children=[
                html.Div(
                    [
                        html.Label("Ensemble"),
                        html.Div(
                            style=self.set_grid_layout("12fr 1fr 1fr"),
                            children=[
                                dcc.Dropdown(
                                    options=[
                                        {"label": ens, "value": ens}
                                        for ens in self.ensembles
                                    ],
                                    value=self.ensembles[0],
                                    id=ensemble_id,
                                    clearable=False,
                                    persistence=True,
                                    persistence_type="session",
                                ),
                                html.Button(
                                    style={
                                        "fontSize": "2rem",
                                        "paddingLeft": "5px",
                                        "paddingRight": "5px",
                                    },
                                    id=ens_prev_id,
                                    children="⬅",
                                ),
                                html.Button(
                                    style={
                                        "fontSize": "2rem",
                                        "paddingLeft": "5px",
                                        "paddingRight": "5px",
                                    },
                                    id=ens_next_id,
                                    children="➡",
                                ),
                            ],
                        ),
                    ]
                ),
                html.Div(
                    children=[
                        html.Label("Realization / Statistic"),
                        html.Div(
                            style=self.set_grid_layout("12fr 1fr 1fr"),
                            children=[
                                dcc.Dropdown(
                                    options=[
                                        {"label": real, "value": real}
                                        for real in self.realizations(self.ensembles[0])
                                    ],
                                    value=self.realizations(self.ensembles[0])[0],
                                    id=real_id,
                                    clearable=False,
                                    persistence=True,
                                    persistence_type="session",
                                ),
                                html.Button(
                                    style={
                                        "fontSize": "2rem",
                                        "paddingLeft": "5px",
                                        "paddingRight": "5px",
                                    },
                                    id=real_prev_id,
                                    children="⬅",
                                ),
                                html.Button(
                                    style={
                                        "fontSize": "2rem",
                                        "paddingLeft": "5px",
                                        "paddingRight": "5px",
                                    },
                                    id=real_next_id,
                                    children="➡",
                                ),
                            ],
                        ),
                    ]
                ),
            ]
        )

    @property
    def layout(self) -> html.Div:
        return html.Div(
            id=self.uuid("layout"),
            children=[
                wcc.FlexBox(
                    style={"fontSize": "1rem"},
                    children=[
                        html.Div(
                            id=self.uuid("settings-view1"),
                            style={"margin": "10px", "flex": 4},
                            children=[
                                self.selector.layout,
                                self.ensemble_layout(
                                    ensemble_id=self.uuid("ensemble"),
                                    ens_prev_id=self.uuid("ensemble-prev"),
                                    ens_next_id=self.uuid("ensemble-next"),
                                    real_id=self.uuid("realization"),
                                    real_prev_id=self.uuid("realization-prev"),
                                    real_next_id=self.uuid("realization-next"),
                                ),
                            ],
                        ),
                        html.Div(
                            style={"margin": "10px", "flex": 4},
                            id=self.uuid("settings-view2"),
                            children=[
                                self.selector2.layout,
                                self.ensemble_layout(
                                    ensemble_id=self.uuid("ensemble2"),
                                    ens_prev_id=self.uuid("ensemble2-prev"),
                                    ens_next_id=self.uuid("ensemble2-next"),
                                    real_id=self.uuid("realization2"),
                                    real_prev_id=self.uuid("realization2-prev"),
                                    real_next_id=self.uuid("realization2-next"),
                                ),
                            ],
                        ),
                        html.Div(
                            style={"margin": "10px", "flex": 4},
                            id=self.uuid("settings-view3"),
                            children=[
                                html.Label("Calculation"),
                                html.Div(
                                    dcc.Dropdown(
                                        id=self.uuid("calculation"),
                                        value="Difference",
                                        clearable=False,
                                        options=[
                                            {"label": i, "value": i}
                                            for i in [
                                                "Difference",
                                                "Sum",
                                                "Product",
                                                "Quotient",
                                            ]
                                        ],
                                        persistence=True,
                                        persistence_type="session",
                                    )
                                ),
                                wcc.FlexBox(
                                    children=[
                                        html.Div(
                                            style={"width": "20%", "flex": 1},
                                            children=[
                                                html.Label("Truncate Min"),
                                                dcc.Input(
                                                    debounce=True,
                                                    type="number",
                                                    id=self.uuid("truncate-diff-min"),
                                                    persistence=True,
                                                    persistence_type="session",
                                                ),
                                            ],
                                        ),
                                        html.Div(
                                            style={"width": "20%", "flex": 1},
                                            children=[
                                                html.Label("Truncate Max"),
                                                dcc.Input(
                                                    debounce=True,
                                                    type="number",
                                                    id=self.uuid("truncate-diff-max"),
                                                    persistence=True,
                                                    persistence_type="session",
                                                ),
                                            ],
                                        ),
                                        html.Label(
                                            style={"fontSize": "1.2rem"},
                                            id=self.uuid("map3-label"),
                                        ),
                                    ]
                                ),
                            ],
                        ),
                    ],
                ),
                wcc.FlexBox(
                    style={"fontSize": "1rem"},
                    children=[
                        html.Div(
                            style={
                                "height": self.map_height,
                                "margin": "10px",
                                "flex": 4,
                            },
                            children=[
                                LeafletMap(
                                    syncedMaps=[self.uuid("map2"), self.uuid("map3")],
                                    id=self.uuid("map"),
                                    layers=[],
                                    unitScale={},
                                    autoScaleMap=True,
                                    minZoom=-5,
                                    updateMode="update",
                                    mouseCoords={"position": "bottomright"},
                                    colorBar={"position": "bottomleft"},
                                    switch={
                                        "value": False,
                                        "disabled": False,
                                        "label": "Hillshading",
                                    },
                                ),
                            ],
                        ),
                        html.Div(
                            style={"margin": "10px", "flex": 4},
                            children=[
                                LeafletMap(
                                    syncedMaps=[self.uuid("map"), self.uuid("map3")],
                                    id=self.uuid("map2"),
                                    layers=[],
                                    unitScale={},
                                    autoScaleMap=True,
                                    minZoom=-5,
                                    updateMode="update",
                                    mouseCoords={"position": "bottomright"},
                                    colorBar={"position": "bottomleft"},
                                    switch={
                                        "value": False,
                                        "disabled": False,
                                        "label": "Hillshading",
                                    },
                                )
                            ],
                        ),
                        html.Div(
                            style={"margin": "10px", "flex": 4},
                            children=[
                                LeafletMap(
                                    syncedMaps=[self.uuid("map"), self.uuid("map2")],
                                    id=self.uuid("map3"),
                                    layers=[],
                                    unitScale={},
                                    autoScaleMap=True,
                                    minZoom=-5,
                                    updateMode="update",
                                    mouseCoords={"position": "bottomright"},
                                    colorBar={"position": "bottomleft"},
                                    switch={
                                        "value": False,
                                        "disabled": False,
                                        "label": "Hillshading",
                                    },
                                )
                            ],
                        ),
                        dcc.Store(
                            id=self.uuid("attribute-settings"),
                            data=json.dumps(self.attribute_settings),
                            storage_type="session",
                        ),
                    ],
                ),
            ],
        )

    def get_real_runpath(self, data: dict, ensemble: str, real: str) -> Path:
        filename = make_fmu_filename(data)
        runpath = Path(
            self.ens_df.loc[
                (self.ens_df["ENSEMBLE"] == ensemble) & (self.ens_df["REAL"] == real)
            ]["RUNPATH"].unique()[0]
        )

        return get_path(runpath / "share" / "results" / "maps" / f"{filename}.gri")

    def get_ens_runpath(self, data: dict, ensemble: str) -> List[Path]:
        filename = make_fmu_filename(data)
        runpaths = self.ens_df.loc[(self.ens_df["ENSEMBLE"] == ensemble)][
            "RUNPATH"
        ].unique()
        return [
            Path(runpath) / "share" / "results" / "maps" / f"{filename}.gri"
            for runpath in runpaths
        ]

    def set_callbacks(self, app: dash.Dash) -> None:
        @app.callback(
            [
                Output(self.uuid("map"), "layers"),
                Output(self.uuid("map2"), "layers"),
                Output(self.uuid("map3"), "layers"),
                Output(self.uuid("map3-label"), "children"),
            ],
            [
                Input(self.selector.storage_id, "data"),
                Input(self.uuid("ensemble"), "value"),
                Input(self.uuid("realization"), "value"),
                Input(self.selector2.storage_id, "data"),
                Input(self.uuid("ensemble2"), "value"),
                Input(self.uuid("realization2"), "value"),
                Input(self.uuid("calculation"), "value"),
                Input(self.uuid("attribute-settings"), "data"),
                Input(self.uuid("truncate-diff-min"), "value"),
                Input(self.uuid("truncate-diff-max"), "value"),
                Input(self.uuid("map"), "switch"),
                Input(self.uuid("map2"), "switch"),
                Input(self.uuid("map3"), "switch"),
            ],
        )
        # pylint: disable=too-many-arguments, too-many-locals
        def _set_base_layer(
            stored_selector_data: str,
            ensemble: str,
            real: str,
            stored_selector2_data: str,
            ensemble2: str,
            real2: str,
            calculation: str,
            stored_attribute_settings: str,
            diff_min: Union[int, float, None],
            diff_max: Union[int, float, None],
            hillshade: dict,
            hillshade2: dict,
            hillshade3: dict,
        ) -> Tuple[List[dict], List[dict], List[dict], str]:
            ctx = dash.callback_context.triggered
            if not ctx or not stored_selector_data or not stored_selector2_data:
                raise PreventUpdate

            # TODO(Sigurd)
            # These two are presumably of type dict, but the type depends on the actual python
            # objects that get serialized inside SurfaceSelector.
            # Should deserialization and validation be delegated to SurfaceSelector?
            # Note that according to the doc, it seems that dcc.Store actualy does the
            # serialization/deserialization for us!
            # Should be refactored
            data: dict = json.loads(stored_selector_data)
            data2: dict = json.loads(stored_selector2_data)
            if not isinstance(data, dict) or not isinstance(data2, dict):
                raise TypeError("Selector data payload must be of type dict")

            attribute_settings: dict = json.loads(stored_attribute_settings)
            if not isinstance(attribute_settings, dict):
                raise TypeError("Expected stored attribute_settings to be of type dict")

            if real in ["Mean", "StdDev", "Min", "Max"]:
                surface = calculate_surface(self.get_ens_runpath(data, ensemble), real)

            else:
                surface = load_surface(self.get_real_runpath(data, ensemble, real))
            if real2 in ["Mean", "StdDev", "Min", "Max"]:
                surface2 = calculate_surface(
                    self.get_ens_runpath(data2, ensemble2), real2
                )

            else:
                surface2 = load_surface(self.get_real_runpath(data2, ensemble2, real2))

            surface_layers: List[dict] = [
                SurfaceLeafletModel(
                    surface,
                    name="surface",
                    colors=attribute_settings.get(data["attr"], {}).get("color"),
                    apply_shading=hillshade.get("value", False),
                    clip_min=attribute_settings.get(data["attr"], {}).get("min", None),
                    clip_max=attribute_settings.get(data["attr"], {}).get("max", None),
                    unit=attribute_settings.get(data["attr"], {}).get("unit", " "),
                ).layer
            ]
            surface_layers2: List[dict] = [
                SurfaceLeafletModel(
                    surface2,
                    name="surface2",
                    colors=attribute_settings.get(data2["attr"], {}).get("color"),
                    apply_shading=hillshade2.get("value", False),
                    clip_min=attribute_settings.get(data2["attr"], {}).get("min", None),
                    clip_max=attribute_settings.get(data2["attr"], {}).get("max", None),
                    unit=attribute_settings.get(data2["attr"], {}).get("unit", " "),
                ).layer
            ]

            try:
                surface3 = calculate_surface_difference(surface, surface2, calculation)
                if diff_min is not None:
                    surface3.values[surface3.values <= diff_min] = diff_min
                if diff_max is not None:
                    surface3.values[surface3.values >= diff_max] = diff_max
                diff_layers: List[dict] = []
                diff_layers.append(
                    SurfaceLeafletModel(
                        surface3,
                        name="surface3",
                        colors=attribute_settings.get(data["attr"], {}).get("color"),
                        apply_shading=hillshade3.get("value", False),
                    ).layer
                )
                error_label = ""
            except ValueError:
                diff_layers = []
                error_label = (
                    "Cannot calculate because the surfaces have different geometries"
                )

            if self.well_layer:
                surface_layers.append(self.well_layer)
                surface_layers2.append(self.well_layer)
                diff_layers.append(self.well_layer)
            return (surface_layers, surface_layers2, diff_layers, error_label)

        def _update_from_btn(
            _n_prev: int, _n_next: int, current_value: str, options: List[dict]
        ) -> str:
            """Updates dropdown value if previous/next btn is clicked"""
            option_values: List[str] = [opt["value"] for opt in options]
            ctx = dash.callback_context.triggered
            if not ctx or current_value is None:
                raise PreventUpdate
            if not ctx[0]["value"]:
                return current_value
            callback = ctx[0]["prop_id"]
            if "-prev" in callback:
                return prev_value(current_value, option_values)
            if "-next" in callback:
                return next_value(current_value, option_values)
            return current_value

        for btn_name in ["ensemble", "realization", "ensemble2", "realization2"]:
            app.callback(
                Output(self.uuid(f"{btn_name}"), "value"),
                [
                    Input(self.uuid(f"{btn_name}-prev"), "n_clicks"),
                    Input(self.uuid(f"{btn_name}-next"), "n_clicks"),
                ],
                [
                    State(self.uuid(f"{btn_name}"), "value"),
                    State(self.uuid(f"{btn_name}"), "options"),
                ],
            )(_update_from_btn)

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        store_functions: List[Tuple[Callable, list]] = [
            (
                find_surfaces,
                [
                    {
                        "ensemble_paths": self.ens_paths,
                        "suffix": "*.gri",
                        "delimiter": "--",
                    }
                ],
            )
        ]

        filenames = []
        # Generate all file names
        for attr, values in self.surfaceconfig.items():
            for name in values["names"]:
                for date in values["dates"]:
                    filename = f"{name}--{attr}"
                    if date is not None:
                        filename += f"--{date}"
                    filename += ".gri"
                    filenames.append(filename)

        # Copy all realization files
        for runpath in self.ens_df["RUNPATH"].unique():
            for filename in filenames:
                path = Path(runpath) / "share" / "results" / "maps" / filename
                if path.exists():
                    store_functions.append((get_path, [{"path": path}]))

        # Calculate and store statistics
        for _, ens_df in self.ens_df.groupby("ENSEMBLE"):
            runpaths = list(ens_df["RUNPATH"].unique())
            for filename in filenames:
                paths = [
                    Path(runpath) / "share" / "results" / "maps" / filename
                    for runpath in runpaths
                ]
                for statistic in ["Mean", "StdDev", "Min", "Max"]:
                    store_functions.append(
                        (save_surface, [{"fns": paths, "statistic": statistic}])
                    )
        if self.wellfolder is not None:
            store_functions.append(
                (find_files, [{"folder": self.wellfolder, "suffix": self.wellsuffix}])
            )
        if self.wellfiles is not None:
            store_functions.extend(
                [(get_path, [{"path": fn}]) for fn in self.wellfiles]
            )
        store_functions.append(
            (
                get_realizations,
                [
                    {
                        "ensemble_paths": self.ens_paths,
                        "ensemble_set_name": "EnsembleSet",
                    }
                ],
            )
        )
        return store_functions


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def calculate_surface(fns: List[str], statistic: str) -> xtgeo.RegularSurface:
    return surface_from_json(json.load(save_surface(fns, statistic)))


@webvizstore
def save_surface(fns: List[str], statistic: str) -> io.BytesIO:
    surfaces = xtgeo.Surfaces(fns)
    if len(surfaces.surfaces) == 0:
        surface = xtgeo.RegularSurface()
    elif statistic in ["Mean", "StdDev", "Min", "Max", "P10", "P90"]:
        # Suppress numpy warnings when surfaces have undefined z-values
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", "All-NaN slice encountered")
            warnings.filterwarnings("ignore", "Mean of empty slice")
            warnings.filterwarnings("ignore", "Degrees of freedom <= 0 for slice")
            surface = calculate_statistic(surfaces, statistic)
    else:
        surface = xtgeo.RegularSurface()
    return io.BytesIO(surface_to_json(surface).encode())


# pylint: disable=too-many-return-statements
def calculate_statistic(
    surfaces: xtgeo.Surfaces, statistic: str
) -> xtgeo.RegularSurface:
    if statistic == "Mean":
        return surfaces.apply(np.nanmean, axis=0)
    if statistic == "StdDev":
        return surfaces.apply(np.nanstd, axis=0)
    if statistic == "Min":
        return surfaces.apply(np.nanmin, axis=0)
    if statistic == "Max":
        return surfaces.apply(np.nanmax, axis=0)
    if statistic == "P10":
        return surfaces.apply(np.nanpercentile, 10, axis=0)
    if statistic == "P90":
        return surfaces.apply(np.nanpercentile, 90, axis=0)
    return xtgeo.RegularSurface()


def surface_to_json(surface: xtgeo.RegularSurface) -> str:
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


def surface_from_json(surfaceobj: dict) -> xtgeo.RegularSurface:
    # See https://github.com/equinor/xtgeo/issues/405
    surface = xtgeo.RegularSurface(**surfaceobj)
    surface.values = np.array(surfaceobj["values"])
    return surface


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_surfaces(fns: List[str]) -> xtgeo.Surfaces:
    return xtgeo.Surfaces(fns)


@webvizstore
def get_path(path: Path) -> Path:
    return Path(path)


def prev_value(current_value: str, options: List[str]) -> str:
    try:
        index = options.index(current_value)
        return options[max(0, index - 1)]
    except ValueError:
        return current_value


def next_value(current_value: str, options: List[str]) -> str:
    try:
        index = options.index(current_value)
        return options[min(len(options) - 1, index + 1)]

    except ValueError:
        return current_value


def surfacedf_to_dict(df: pd.DataFrame) -> dict:
    return {
        attr: {
            "names": list(dframe["name"].unique()),
            "dates": list(dframe["date"].unique())
            if "date" in dframe.columns
            else None,
        }
        for attr, dframe in df.groupby("attribute")
    }


@webvizstore
def find_files(folder: Path, suffix: str) -> io.BytesIO:
    return io.BytesIO(
        json.dumps(
            sorted([str(filename) for filename in folder.glob(f"*{suffix}")])
        ).encode()
    )


def make_fmu_filename(data: dict) -> str:
    filename = f"{data['name']}--{data['attr']}"
    if data["date"] is not None:
        filename += f"--{data['date']}"
    return filename


def calculate_surface_difference(
    surface: xtgeo.RegularSurface,
    surface2: xtgeo.RegularSurface,
    calculation: str = "Difference",
) -> xtgeo.RegularSurface:
    surface3 = surface.copy()
    if calculation == "Difference":
        surface3.values = surface3.values - surface2.values
    elif calculation == "Sum":
        surface3.values = surface3.values + surface2.values
    elif calculation == "Product":
        surface3.values = surface3.values * surface2.values
    elif calculation == "Quotient":
        surface3.values = surface3.values / surface2.values
    return surface3
