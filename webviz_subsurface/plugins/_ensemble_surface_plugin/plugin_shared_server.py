from operator import sub
from typing import Callable, Dict, List, Tuple, Optional, Union
from pathlib import Path
import io
import logging

from dataclasses import asdict
from urllib.parse import quote_plus, unquote_plus
from werkzeug.routing import BaseConverter

from flask import send_file
import xtgeo
import dash
from dash import Dash, Input, Output, State, no_update
from dash.long_callback import DiskcacheLongCallbackManager

from webviz_config import WebvizPluginABC, WebvizSettings


from webviz_subsurface._providers import (
    EnsembleSurfaceProviderFactory,
    EnsembleSurfaceProvider,
)
from webviz_subsurface._providers.ensemble_surface_provider.ensemble_surface_provider import (
    SurfaceStatistic,
    SimulatedSurfaceAddress,
    StatisticalSurfaceAddress,
)
from webviz_subsurface._providers.ensemble_surface_provider.surface_server_lazy import (
    SurfaceServerLazy,
)
from webviz_subsurface._providers.ensemble_surface_provider.surface_server_eager import (
    SurfaceServerEager,
    QualifiedAddress,
    QualifiedDiffAddress,
)

import webviz_core_components as wcc
import webviz_subsurface_components as wsc

from ._make_rgba import surface_to_rgba

from ._layout import main_layout

import diskcache

cache = diskcache.Cache("./cache_for_testing_long_callbacks")
long_callback_manager = DiskcacheLongCallbackManager(cache)

LOGGER = logging.getLogger(__name__)


class EnsembleSurfaceSharedServer(WebvizPluginABC):
    """ """

    def __init__(
        self,
        app: Dash,
        ensemble: str,
        webviz_settings: WebvizSettings,
    ):
        super().__init__()
        self.app = app
        provider_factory = EnsembleSurfaceProviderFactory.instance()
        self.provider: EnsembleSurfaceProvider = (
            provider_factory.create_from_ensemble_surface_files(
                webviz_settings.shared_settings["scratch_ensembles"][ensemble]
            )
        )

        # self.lazy_surf_server: Optional[SurfaceServerLazy] = None
        # self.lazy_surf_server = SurfaceServerLazy.instance(app)
        # self.lazy_surf_server.add_provider(self.provider)
        self.eager_surf_server: Optional[SurfaceServerEager] = None
        self.eager_surf_server = SurfaceServerEager.instance(app)

        # self._attribute = "ds_extract_postprocess"
        self._attribute = "ds_extract_postprocess-refined4"
        # self._attribute = "ds_extract_postprocess-refined8"
        self._name = self.provider.surface_names_for_attribute(self._attribute)[0]
        self._datestr = self.provider.surface_dates_for_attribute(self._attribute)[0]
        self._realization = self.provider.realizations()[0]

        self.set_callbacks(app)

    @property
    def layout(self) -> wcc.FlexBox:
        return main_layout(get_uuid=self.uuid)

    def set_callbacks(self, app):
        # @app.long_callback(
        #     Output(self.uuid("map-component"), "layers"),
        #     Output(self.uuid("map-component"), "bounds"),
        #     Input(self.uuid("mode"), "value"),
        #     State(self.uuid("map-component"), "layers"),
        #     interval_time=100,
        #     manager=long_callback_manager,
        # )
        @app.callback(
            Output(self.uuid("map-component"), "layers"),
            Output(self.uuid("map-component"), "bounds"),
            Input(self.uuid("mode"), "value"),
            State(self.uuid("map-component"), "layers"),
        )
        def _update_surface(mode: str, layers: List[Dict]) -> List[Dict]:

            print(f"START CALLBACK  {self._plugin_uuid}")

            # ctx = dash.callback_context
            # print(f"ctx.triggered  {ctx.triggered}")
            # print(f"ctx.inputs  {ctx.inputs}")
            # print(f"ctx.states  {ctx.states}")

            provider_id: str = self.provider.provider_id()

            if mode == "Realization":
                surface_address = SimulatedSurfaceAddress(
                    attribute=self._attribute,
                    name=self._name,
                    datestr=self._datestr,
                    realization=int(self._realization),
                )
            else:
                surface_address = StatisticalSurfaceAddress(
                    attribute=self._attribute,
                    name=self._name,
                    datestr=self._datestr,
                    realizations=[int(real) for real in self.provider.realizations()],
                    statistic=SurfaceStatistic(mode),
                )

            sub_surface_address = None
            # sub_surface_address = StatisticalSurfaceAddress(
            #     attribute=self._attribute,
            #     name=self._name,
            #     datestr=self._datestr,
            #     realizations=[int(real) for real in self.provider.realizations()],
            #     statistic=SurfaceStatistic.MEAN,
            # )

            qualified_address: Union[QualifiedAddress, QualifiedDiffAddress]
            if sub_surface_address:
                qualified_address = QualifiedDiffAddress(
                    provider_id, surface_address, provider_id, sub_surface_address
                )
            else:
                qualified_address = QualifiedAddress(provider_id, surface_address)

            surf_meta = self.eager_surf_server.get_surface_metadata(qualified_address)
            if not surf_meta:
                # This means we need to comput the surface
                if sub_surface_address:
                    LOGGER.debug(
                        f"Getting/calculating DIFF surface for: {surface_address}-{sub_surface_address}"
                    )
                    surface_a = self.provider.get_surface(address=surface_address)
                    surface_b = self.provider.get_surface(address=sub_surface_address)
                    surface = surface_a - surface_b
                else:
                    LOGGER.debug(f"Getting/calculating surface for: {surface_address}")
                    surface = self.provider.get_surface(address=surface_address)
                    if not surface:
                        raise ValueError(
                            f"Could not get surface for address: {surface_address}"
                        )

                self.eager_surf_server.publish_surface(qualified_address, surface)
                surf_meta = self.eager_surf_server.get_surface_metadata(
                    qualified_address
                )

            bounds = [
                surf_meta.x_min,
                surf_meta.y_min,
                surf_meta.x_max,
                surf_meta.y_max,
            ]
            layers[0]["bounds"] = bounds
            layers[0]["valueRange"] = [surf_meta.val_min, surf_meta.val_max]
            # layers[0]["rotDeg"] = 30

            surface_url = self.eager_surf_server.encode_partial_url(qualified_address)
            print("EAGER SURFACE_URL:", surface_url)

            layers[0]["image"] = surface_url

            print(f"END CALLBACK {self._plugin_uuid}")

            return layers, bounds
