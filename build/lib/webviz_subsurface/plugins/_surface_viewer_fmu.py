import io
import json
from pathlib import Path
from typing import Callable, List, Tuple, Union

import pandas as pd
import webviz_core_components as wcc
import xtgeo
from dash import Dash, Input, Output, State, callback_context, dcc, html
from dash.exceptions import PreventUpdate
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.deprecation_decorators import deprecated_plugin
from webviz_config.webviz_store import webvizstore
from webviz_subsurface_components import LeafletMap

from webviz_subsurface._datainput.fmu_input import find_surfaces, get_realizations
from webviz_subsurface._datainput.well import make_well_layers
from webviz_subsurface._models import SurfaceLeafletModel, SurfaceSetModel
from webviz_subsurface._private_plugins.surface_selector import SurfaceSelector


@deprecated_plugin("Relevant functionality is implemented in the MapViewerFMU plugin.")
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
        app: Dash,
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
        self._surface_table = find_surfaces(self.ens_paths)
        # Extract realizations and sensitivity information
        self.ens_df = get_realizations(
            ensemble_paths=self.ens_paths, ensemble_set_name="EnsembleSet"
        )

        # Drop any ensembles that does not have surfaces
        self.ens_df = self.ens_df.loc[
            self.ens_df["ENSEMBLE"].isin(self._surface_table["ENSEMBLE"].unique())
        ]

        if attributes is not None:
            self._surface_table = self._surface_table[
                self._surface_table["attribute"].isin(attributes)
            ]
            if self._surface_table.empty:
                raise ValueError("No surfaces found with the given attributes")
        self._surface_ensemble_set_model = {
            ens: SurfaceSetModel(surf_ens_df)
            for ens, surf_ens_df in self._surface_table.groupby("ENSEMBLE")
        }
        self.attribute_settings: dict = attribute_settings if attribute_settings else {}
        self.map_height = map_height
        self.surfaceconfig = surfacedf_to_dict(self._surface_table)
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
                                    minZoom=-19,
                                    updateMode="replace",
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
                                    minZoom=-19,
                                    updateMode="replace",
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
                                    minZoom=-19,
                                    updateMode="replace",
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

    def set_callbacks(self, app: Dash) -> None:
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
            ctx = callback_context.triggered
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
                surface = self._surface_ensemble_set_model[
                    ensemble
                ].calculate_statistical_surface(**data, calculation=real)

            else:
                surface = self._surface_ensemble_set_model[
                    ensemble
                ].get_realization_surface(**data, realization=int(real))

            if real2 in ["Mean", "StdDev", "Min", "Max"]:
                surface2 = self._surface_ensemble_set_model[
                    ensemble2
                ].calculate_statistical_surface(**data2, calculation=real2)

            else:
                surface2 = self._surface_ensemble_set_model[
                    ensemble2
                ].get_realization_surface(**data2, realization=int(real2))

            surface_layers: List[dict] = [
                SurfaceLeafletModel(
                    surface,
                    name="surface",
                    colors=attribute_settings.get(data["attribute"], {}).get("color"),
                    apply_shading=hillshade.get("value", False),
                    clip_min=attribute_settings.get(data["attribute"], {}).get(
                        "min", None
                    ),
                    clip_max=attribute_settings.get(data["attribute"], {}).get(
                        "max", None
                    ),
                    unit=attribute_settings.get(data["attribute"], {}).get("unit", " "),
                ).layer
            ]
            surface_layers2: List[dict] = [
                SurfaceLeafletModel(
                    surface2,
                    name="surface2",
                    colors=attribute_settings.get(data2["attribute"], {}).get("color"),
                    apply_shading=hillshade2.get("value", False),
                    clip_min=attribute_settings.get(data2["attribute"], {}).get(
                        "min", None
                    ),
                    clip_max=attribute_settings.get(data2["attribute"], {}).get(
                        "max", None
                    ),
                    unit=attribute_settings.get(data2["attribute"], {}).get(
                        "unit", " "
                    ),
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
                        colors=attribute_settings.get(data["attribute"], {}).get(
                            "color"
                        ),
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
            ctx = callback_context.triggered
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
        for ens in list(self.ens_df["ENSEMBLE"].unique()):
            for calculation in ["Mean", "StdDev", "Min", "Max"]:
                store_functions.append(
                    self._surface_ensemble_set_model[
                        ens
                    ].webviz_store_statistical_calculation(calculation=calculation)
                )
            store_functions.append(
                self._surface_ensemble_set_model[
                    ens
                ].webviz_store_realization_surfaces()
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


def calculate_surface_difference(
    surface: xtgeo.RegularSurface,
    surface2: xtgeo.RegularSurface,
    calculation: str = "Difference",
) -> xtgeo.RegularSurface:
    if calculation == "Difference":
        calculated_surface = surface - surface2
    elif calculation == "Sum":
        calculated_surface = surface + surface2
    elif calculation == "Product":
        calculated_surface = surface * surface2
    elif calculation == "Quotient":
        calculated_surface = surface / surface2
    return calculated_surface
