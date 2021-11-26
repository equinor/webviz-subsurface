from typing import Callable, List, Tuple
from pathlib import Path
import json

from dash import Dash, dcc, html
import pydeck as pdk
from webviz_config import WebvizPluginABC, WebvizSettings
import webviz_core_components as wcc

from webviz_subsurface._models.well_set_model import WellSetModel
from webviz_subsurface._utils.webvizstore_functions import find_files
from webviz_subsurface._datainput.fmu_input import find_surfaces
from webviz_subsurface._components import DeckGLMapAIO
from webviz_subsurface._components.deckgl_map.data_loaders import (
    XtgeoWellsJson,
    XtgeoLogsJson,
)
from webviz_subsurface._components.deckgl_map.deckgl_map import (
    WellsLayer,
    ColormapLayer,
    Hillshading2DLayer,
)
from .callbacks.deckgl_map_aio_callbacks import (
    deckgl_map_aio_callbacks,
)
from webviz_subsurface.plugins._map_viewer_fmu.layout.data_selector_view import (
    well_selector_view,
)

from .models import SurfaceSetModel
from .layout import surface_selector_view, surface_settings_view
from .routes import deckgl_map_routes
from .callbacks import surface_selector_callbacks
from .webviz_store import webviz_store_functions


class MapViewerFMU(WebvizPluginABC):
    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        attributes: list = None,
        wellfolder: Path = None,
        wellsuffix: str = ".w",
        well_downsample_interval: int = None,
        mdlog: str = None,
    ):

        super().__init__()
        with open("/tmp/drogon_well_picks.json", "r") as f:
            self.jsondata = json.load(f)
        self.ens_paths = {
            ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
            for ens in ensembles
        }
        self._wellfolder = wellfolder
        self._wellsuffix = wellsuffix
        self._wellfiles: List = (
            json.load(find_files(folder=self._wellfolder, suffix=self._wellsuffix))
            if self._wellfolder is not None
            else None
        )
        # Find surfaces
        self._surface_table = find_surfaces(self.ens_paths)

        if attributes is not None:
            self._surface_table = self._surface_table[
                self._surface_table["attribute"].isin(attributes)
            ]
            if self._surface_table.empty:
                raise ValueError("No surfaces found with the given attributes")
        self._surface_ensemble_set_models = {
            ens: SurfaceSetModel(surf_ens_df)
            for ens, surf_ens_df in self._surface_table.groupby("ENSEMBLE")
        }
        self._well_set_model = (
            WellSetModel(
                self._wellfiles,
                mdlog=mdlog,
                downsample_interval=well_downsample_interval,
            )
            if self._wellfiles
            else None
        )

        self.set_callbacks()
        self.set_routes(app)

    @property
    def layout(self) -> html.Div:
        selector_views = [
            surface_selector_view(
                get_uuid=self.uuid,
                surface_set_models=self._surface_ensemble_set_models,
            )
        ]
        if self._well_set_model is not None:
            selector_views.append(
                well_selector_view(
                    get_uuid=self.uuid, well_set_model=self._well_set_model
                )
            )
        return html.Div(
            id=self.uuid("layout"),
            children=[
                wcc.FlexBox(
                    children=[
                        wcc.Frame(
                            style={"flex": 1, "height": "90vh"},
                            children=selector_views,
                        ),
                        wcc.Frame(
                            style={
                                "flex": 5,
                            },
                            children=[
                                DeckGLMapAIO(
                                    aio_id=self.uuid("mapview"),
                                    layers=[
                                        ColormapLayer(),
                                        Hillshading2DLayer(),
                                        WellsLayer(data={}),
                                        pdk.Layer(
                                            "GeoJsonLayer",
                                            self.jsondata,
                                            visible=True,
                                            # get_elevation="properties.valuePerSqm / 20",
                                            # get_fill_color="[255, 255, properties.growth * 255]",
                                            get_line_color=[255, 255, 255],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        wcc.Frame(
                            style={"flex": 1},
                            children=[
                                surface_settings_view(
                                    get_uuid=self.uuid,
                                ),
                            ],
                        ),
                        dcc.Store(
                            id=self.uuid("surface-geometry"),
                        ),
                    ],
                ),
            ],
        )

    def set_callbacks(self) -> None:
        surface_selector_callbacks(
            get_uuid=self.uuid, surface_set_models=self._surface_ensemble_set_models
        )
        deckgl_map_aio_callbacks(
            get_uuid=self.uuid,
            surface_set_models=self._surface_ensemble_set_models,
            well_set_model=self._well_set_model,
        )

    def set_routes(self, app) -> None:
        deckgl_map_routes(
            app=app,
            surface_set_models=self._surface_ensemble_set_models,
            well_set_model=self._well_set_model,
        )

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:

        return webviz_store_functions(
            surface_set_models=self._surface_ensemble_set_models,
            ensemble_paths=self.ens_paths,
        )
