from typing import Dict, List
import io
from uuid import uuid4
from dataclasses import asdict
import json

from flask import send_file
import flask_caching
from dash import Dash, Input, Output, State

from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.common_cache import CACHE


from webviz_subsurface._providers import (
    EnsembleSurfaceProviderFactory,
    EnsembleSurfaceProvider,
)
from webviz_subsurface._providers.ensemble_surface_provider.ensemble_surface_provider import (
    SurfaceStatistic,
    SimulatedSurfaceAddress,
    StatisticalSurfaceAddress,
)

import webviz_core_components as wcc

from ._make_rgba import surface_to_rgba
from ._layout import main_layout


class EnsembleSurfaceCached(WebvizPluginABC):
    """ """

    def __init__(
        self,
        app: Dash,
        ensemble: str,
        webviz_settings: WebvizSettings,
    ):
        super().__init__()
        self.app = app
        # Test redis
        # self.cache = CACHE
        self.cache = flask_caching.Cache(
            config={
                "CACHE_TYPE": "RedisCache",
                "CACHE_KEY_PREFIX": self.uuid(""),
                "CACHE_REDIS_HOST": "localhost",
                "CACHE_REDIS_PORT": 6379,
                "CACHE_REDIS_URL": "redis://localhost:6379",
            }
        )
        self.cache.init_app(app.server)
        provider_factory = EnsembleSurfaceProviderFactory.instance()
        self.provider: EnsembleSurfaceProvider = (
            provider_factory.create_from_ensemble_surface_files(
                webviz_settings.shared_settings["scratch_ensembles"][ensemble]
            )
        )

        self._attribute = "ds_extract_postprocess"
        self._name = self.provider.surface_names_for_attribute(self._attribute)[0]
        self._datestr = self.provider.surface_dates_for_attribute(self._attribute)[0]
        self._realization = self.provider.realizations()[0]

        self.set_callbacks(app)
        self.set_routes(app)

    @property
    def layout(self) -> wcc.FlexBox:
        return main_layout(get_uuid=self.uuid)

    def set_callbacks(self, app):
        @app.callback(
            Output(self.uuid("map-component"), "layers"),
            Output(self.uuid("map-component"), "bounds"),
            Input(self.uuid("mode"), "value"),
            State(self.uuid("map-component"), "layers"),
        )
        def _update_surface(mode: str, layers: List[Dict]) -> List[Dict]:
            if mode == "Realization":
                surface_address = SimulatedSurfaceAddress(
                    attribute=self._attribute,
                    name=self._name,
                    datestr=self._datestr,
                    realization=int(
                        self._realization
                    ),  # np.int is not json serializable out of the box
                )
            else:
                surface_address = StatisticalSurfaceAddress(
                    attribute=self._attribute,
                    name=self._name,
                    datestr=self._datestr,
                    realizations=[int(real) for real in self.provider.realizations()],
                    statistic=SurfaceStatistic.MEAN,
                )
            surface = self.provider.get_surface(address=surface_address)
            bounds = [
                surface.xmin,
                surface.ymin,
                surface.xmax,
                surface.ymax,
            ]
            layers[0]["bounds"] = bounds
            layers[0]["valueRange"] = [surface.values.min(), surface.values.max()]

            # Create some unique hash for the selected surface to use as key in cache
            cached_key = self.uuid(json.dumps(asdict(surface_address)))

            # Create the map image and add to local/redis key,value cache if it is not already there
            if self.cache.get(cached_key) is None:
                img = surface_to_rgba(surface)
                self.cache.add(cached_key, img)
            # Set the URI to the cache key
            layers[0]["image"] = f"/from_dash_callback/{cached_key}.png"

            return layers, bounds

    def set_routes(self, app):
        @app.server.route("/from_dash_callback/<cached_key>.<filetype>")
        def _send_surface_as_png2(cached_key: str, filetype: str):
            """Endpoint to retrieve data from cache"""
            cached_data = self.cache.get(cached_key)
            if cached_data is None:
                # abort
                ...
            if filetype == "png":
                cached_img = self.cache.get(cached_key)
                return send_file(io.BytesIO(cached_img), mimetype="image/png")
            if filetype == "json":
                ...
            ...
