from typing import Callable, List, Tuple

from dash import Dash, dcc, html
from webviz_config import WebvizPluginABC, WebvizSettings
import webviz_core_components as wcc

from webviz_subsurface._datainput.fmu_input import find_surfaces
from webviz_subsurface._components import DeckGLMapAIO
from webviz_subsurface.plugins._map_viewer_fmu.callbacks.deckgl_map_aio_callbacks import (
    deckgl_map_aio_callbacks,
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
    ):

        super().__init__()

        self.ens_paths = {
            ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
            for ens in ensembles
        }

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

        self.set_callbacks()
        self.set_routes(app)

    @property
    def layout(self) -> html.Div:
        return html.Div(
            id=self.uuid("layout"),
            children=[
                wcc.FlexBox(
                    children=[
                        wcc.Frame(
                            style={"flex": 1, "height": "90vh"},
                            children=[
                                surface_selector_view(
                                    get_uuid=self.uuid,
                                    surface_set_models=self._surface_ensemble_set_models,
                                ),
                            ],
                        ),
                        wcc.Frame(
                            style={
                                "flex": 5,
                            },
                            children=[
                                DeckGLMapAIO(aio_id=self.uuid("mapview")),
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
            get_uuid=self.uuid, surface_set_models=self._surface_ensemble_set_models
        )

    def set_routes(self, app) -> None:
        deckgl_map_routes(app=app, surface_set_models=self._surface_ensemble_set_models)

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:

        return webviz_store_functions(
            surface_set_models=self._surface_ensemble_set_models,
            ensemble_paths=self.ens_paths,
        )
