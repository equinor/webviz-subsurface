# pylint: skip-file
import io
import json
import logging
from dataclasses import asdict
from typing import Dict, Optional, Union
from urllib.parse import quote_plus, unquote_plus
from uuid import uuid4

import flask
import flask_caching
from dash import Dash

from webviz_subsurface._utils.perf_timer import PerfTimer

from ._surface_to_image import surface_to_png_bytes
from .ensemble_surface_provider import (
    EnsembleSurfaceProvider,
    ObservedSurfaceAddress,
    SimulatedSurfaceAddress,
    StatisticalSurfaceAddress,
)

LOGGER = logging.getLogger(__name__)
ROOT_URL_PATH = "/SurfaceServerLazy"


class SurfaceServerLazy:
    def __init__(self, app: Dash) -> None:
        self._dash_app: Dash = app
        self._id_to_provider_dict: Dict[str, EnsembleSurfaceProvider] = {}

        self._image_cache = None
        # self._image_cache = flask_caching.Cache(
        #     config={
        #         "CACHE_TYPE": "RedisCache",
        #         "CACHE_KEY_PREFIX": f"SurfaceServer_{uuid4()}",
        #         "CACHE_REDIS_HOST": "localhost",
        #         "CACHE_REDIS_PORT": 6379,
        #         "CACHE_REDIS_URL": "redis://localhost:6379",
        #     }
        # )
        # self._image_cache = flask_caching.Cache(
        #     config={
        #         "CACHE_TYPE": "FileSystemCache",
        #         "CACHE_DIR": "/home/sigurdp/buf/flask_filesys_cache",
        #     }
        # )
        # self._image_cache.init_app(app.server)

    @staticmethod
    def instance(app: Dash) -> "SurfaceServerLazy":
        global SURFACE_SERVER_INSTANCE
        if not SURFACE_SERVER_INSTANCE:
            LOGGER.debug("Initializing SurfaceServerLazy instance")
            SURFACE_SERVER_INSTANCE = SurfaceServerLazy(app)

        return SURFACE_SERVER_INSTANCE

    def add_provider(self, provider: EnsembleSurfaceProvider) -> None:
        # Setup the url rule (our route) when the first provider is added
        if not self._id_to_provider_dict:
            self._setup_url_rule()

        provider_id = provider.provider_id()
        LOGGER.debug(f"Adding provider with id={provider_id}")

        existing_provider = self._id_to_provider_dict.get(provider_id)
        if existing_provider:
            # Issue a warning if there already is a provider registered with the same
            # id AND if the actual provider instance is different.
            # This should not be a problem, but will happen until the provider factory
            # gets caching.
            if existing_provider is not provider:
                LOGGER.warning(
                    f"Provider with id={provider_id} ignored, the id is already present"
                )
                return

        self._id_to_provider_dict[provider_id] = provider

        # routes = []
        # for rule in self._dash_app.server.url_map.iter_rules():
        #     routes.append("%s" % rule)

        # for route in routes:
        #     print(route)

    def encode_partial_url(
        self,
        provider_id: str,
        address: Union[
            StatisticalSurfaceAddress, SimulatedSurfaceAddress, ObservedSurfaceAddress
        ],
    ) -> str:
        if not provider_id in self._id_to_provider_dict:
            raise ValueError("Could not find provider")

        if isinstance(address, StatisticalSurfaceAddress):
            addr_type_str = "sta"
        elif isinstance(address, SimulatedSurfaceAddress):
            addr_type_str = "sim"
        elif isinstance(address, ObservedSurfaceAddress):
            addr_type_str = "obs"

        surf_address_str = quote_plus(json.dumps(asdict(address)))

        url_path: str = (
            f"{ROOT_URL_PATH}/{provider_id}/{addr_type_str}/{surf_address_str}"
        )
        return url_path

    def _setup_url_rule(self) -> None:
        @self._dash_app.server.route(
            ROOT_URL_PATH + "/<provider_id>/<addr_type_str>/<surf_address_str>"
        )
        def _handle_request(
            provider_id: str, addr_type_str: str, surf_address_str: str
        ) -> flask.Response:
            LOGGER.debug(
                f"Handling request: "
                f"provider_id={provider_id} "
                f"addr_type_str={addr_type_str} "
                f"surf_address_str={surf_address_str}"
            )

            timer = PerfTimer()

            try:
                provider = self._id_to_provider_dict[provider_id]
                surf_address_dict = json.loads(unquote_plus(surf_address_str))
                address: Union[
                    StatisticalSurfaceAddress,
                    SimulatedSurfaceAddress,
                    ObservedSurfaceAddress,
                ]
                if addr_type_str == "sta":
                    address = StatisticalSurfaceAddress(**surf_address_dict)
                if addr_type_str == "sim":
                    address = SimulatedSurfaceAddress(**surf_address_dict)
                if addr_type_str == "obs":
                    address = ObservedSurfaceAddress(**surf_address_dict)
            except:
                LOGGER.error("Error decoding surface address")
                flask.abort(404)

            if self._image_cache:
                img_cache_key = (
                    f"provider_id={provider_id} "
                    f"addr_type={addr_type_str} address={surf_address_str}"
                )
                LOGGER.debug(
                    f"Looking for image in cache (key={img_cache_key}, "
                    f"cache_type={self._image_cache.config['CACHE_TYPE']})"
                )
                cached_img_bytes = self._image_cache.get(img_cache_key)
                if cached_img_bytes:
                    response = flask.send_file(
                        io.BytesIO(cached_img_bytes), mimetype="image/png"
                    )
                    LOGGER.debug(
                        f"Request handled from image cache in: {timer.elapsed_s():.2f}s"
                    )
                    return response

            LOGGER.debug("Getting surface from provider...")
            timer.lap_s()
            surface = provider.get_surface(address)
            if not surface:
                LOGGER.error(f"Error getting surface for address: {address}")
                flask.abort(404)
            et_get_s = timer.lap_s()
            LOGGER.debug(
                f"Got surface (dimensions={surface.dimensions}, #cells={surface.ncol*surface.nrow})"
            )

            LOGGER.debug("Converting to PNG image...")
            png_bytes: bytes = surface_to_png_bytes(surface)
            LOGGER.debug(
                f"Got PNG image, size={(len(png_bytes) / (1024 * 1024)):.2f}MB"
            )
            et_to_image_s = timer.lap_s()

            LOGGER.debug("Sending image")
            response = flask.send_file(io.BytesIO(png_bytes), mimetype="image/png")
            et_send_s = timer.lap_s()

            if self._image_cache and img_cache_key:
                self._image_cache.add(img_cache_key, png_bytes)

            LOGGER.debug(
                f"Request handled in: {timer.elapsed_s():.2f}s ("
                f"get={et_get_s:.2f}s, to_image={et_to_image_s:.2f}s, send={et_send_s:.2f}s)"
            )

            return response


SURFACE_SERVER_INSTANCE: Optional[SurfaceServerLazy] = None
