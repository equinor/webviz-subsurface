import hashlib
import io
import json
import logging
import math
from dataclasses import asdict, dataclass
from typing import List, Optional, Tuple, Union
from urllib.parse import quote
from uuid import uuid4

import flask
import flask_caching
import xtgeo
from dash import Dash
from webviz_config.webviz_instance_info import WEBVIZ_INSTANCE_INFO

from webviz_subsurface._utils.perf_timer import PerfTimer

from ._surface_to_image import surface_to_png_bytes_optimized
from ._types import QualifiedDiffSurfaceAddress, QualifiedSurfaceAddress
from .ensemble_surface_provider import (
    ObservedSurfaceAddress,
    SimulatedSurfaceAddress,
    StatisticalSurfaceAddress,
    SurfaceAddress,
)

LOGGER = logging.getLogger(__name__)

_ROOT_URL_PATH = "/SurfaceImageServer"

_SURFACE_SERVER_INSTANCE: Optional["SurfaceImageServer"] = None


@dataclass(frozen=True)
class SurfaceImageMeta:
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    val_min: float
    val_max: float
    deckgl_bounds: List[float]
    deckgl_rot_deg: float  # Around upper left corner


class SurfaceImageServer:
    def __init__(self, app: Dash) -> None:
        cache_dir = (
            WEBVIZ_INSTANCE_INFO.storage_folder
            / f"SurfaceImageServer_filecache_{uuid4()}"
        )
        LOGGER.debug(f"Setting up file cache in: {cache_dir}")
        self._image_cache = flask_caching.Cache(
            config={
                "CACHE_TYPE": "FileSystemCache",
                "CACHE_DIR": cache_dir,
                "CACHE_DEFAULT_TIMEOUT": 0,
                "CACHE_OPTIONS": {"mode": 0o660},
            }
        )
        self._image_cache.init_app(app.server)

        self._setup_url_rule(app)

    @staticmethod
    def instance(app: Dash) -> "SurfaceImageServer":
        # pylint: disable=global-statement
        global _SURFACE_SERVER_INSTANCE
        if not _SURFACE_SERVER_INSTANCE:
            LOGGER.debug("Initializing SurfaceImageServer instance")
            _SURFACE_SERVER_INSTANCE = SurfaceImageServer(app)

        return _SURFACE_SERVER_INSTANCE

    def publish_surface(
        self,
        qualified_address: Union[QualifiedSurfaceAddress, QualifiedDiffSurfaceAddress],
        surface: xtgeo.RegularSurface,
    ) -> None:
        timer = PerfTimer()

        if isinstance(qualified_address, QualifiedSurfaceAddress):
            base_cache_key = _address_to_str(
                qualified_address.provider_id, qualified_address.address
            )
        else:
            base_cache_key = _diff_address_to_str(
                qualified_address.provider_id_a,
                qualified_address.address_a,
                qualified_address.provider_id_b,
                qualified_address.address_b,
            )

        LOGGER.debug(
            f"Publishing surface (dim={surface.dimensions}, #cells={surface.ncol*surface.nrow}), "
            f"[base_cache_key={base_cache_key}]"
        )

        self._create_and_store_image_in_cache(base_cache_key, surface)

        LOGGER.debug(f"Surface published in: {timer.elapsed_s():.2f}s")

    def get_surface_metadata(
        self,
        qualified_address: Union[QualifiedSurfaceAddress, QualifiedDiffSurfaceAddress],
    ) -> Optional[SurfaceImageMeta]:

        if isinstance(qualified_address, QualifiedSurfaceAddress):
            base_cache_key = _address_to_str(
                qualified_address.provider_id, qualified_address.address
            )
        else:
            base_cache_key = _diff_address_to_str(
                qualified_address.provider_id_a,
                qualified_address.address_a,
                qualified_address.provider_id_b,
                qualified_address.address_b,
            )

        meta_cache_key = "META:" + base_cache_key
        meta: Optional[SurfaceImageMeta] = self._image_cache.get(meta_cache_key)
        if not meta:
            return None

        if not isinstance(meta, SurfaceImageMeta):
            LOGGER.error("Error loading SurfaceImageMeta from cache")
            return None

        return meta

    @staticmethod
    def encode_partial_url(
        qualified_address: Union[QualifiedSurfaceAddress, QualifiedDiffSurfaceAddress],
    ) -> str:

        if isinstance(qualified_address, QualifiedSurfaceAddress):
            address_str = _address_to_str(
                qualified_address.provider_id, qualified_address.address
            )
        else:
            address_str = _diff_address_to_str(
                qualified_address.provider_id_a,
                qualified_address.address_a,
                qualified_address.provider_id_b,
                qualified_address.address_b,
            )

        url_path: str = f"{_ROOT_URL_PATH}/{quote(address_str)}"
        return url_path

    def _setup_url_rule(self, app: Dash) -> None:
        @app.server.route(_ROOT_URL_PATH + "/<full_surf_address_str>")
        def _handle_surface_request(full_surf_address_str: str) -> flask.Response:
            LOGGER.debug(
                f"Handling surface_request: "
                f"full_surf_address_str={full_surf_address_str} "
            )

            timer = PerfTimer()

            img_cache_key = "IMG:" + full_surf_address_str
            LOGGER.debug(f"Looking for image in cache (key={img_cache_key}")

            cached_img_bytes = self._image_cache.get(img_cache_key)
            if not cached_img_bytes:
                LOGGER.error(
                    f"Error getting image for address: {full_surf_address_str}"
                )
                flask.abort(404)

            response = flask.send_file(
                io.BytesIO(cached_img_bytes), mimetype="image/png"
            )
            LOGGER.debug(
                f"Request handled from image cache in: {timer.elapsed_s():.2f}s"
            )
            return response

    def _create_and_store_image_in_cache(
        self,
        base_cache_key: str,
        surface: xtgeo.RegularSurface,
    ) -> None:

        timer = PerfTimer()
        LOGGER.debug("Converting surface to PNG image...")
        png_bytes: bytes = surface_to_png_bytes_optimized(surface)
        LOGGER.debug(f"Got PNG image, size={(len(png_bytes) / (1024 * 1024)):.2f}MB")
        et_to_image_s = timer.lap_s()

        img_cache_key = "IMG:" + base_cache_key
        meta_cache_key = "META:" + base_cache_key

        self._image_cache.add(img_cache_key, png_bytes)

        # For debugging rotations
        # unrot_surf = surface.copy()
        # unrot_surf.unrotate()
        # unrot_surf.quickplot("/home/sigurdp/gitRoot/hk-webviz-subsurface/quickplot.png")

        deckgl_bounds, deckgl_rot = _calc_map_component_bounds_and_rot(surface)

        meta = SurfaceImageMeta(
            x_min=surface.xmin,
            x_max=surface.xmax,
            y_min=surface.ymin,
            y_max=surface.ymax,
            val_min=surface.values.min(),
            val_max=surface.values.max(),
            deckgl_bounds=deckgl_bounds,
            deckgl_rot_deg=deckgl_rot,
        )
        self._image_cache.add(meta_cache_key, meta)
        et_write_cache_s = timer.lap_s()

        LOGGER.debug(
            f"Created image and wrote to cache in in: {timer.elapsed_s():.2f}s ("
            f"to_image={et_to_image_s:.2f}s, write_cache={et_write_cache_s:.2f}s), "
            f"[base_cache_key={base_cache_key}]"
        )


def _address_to_str(
    provider_id: str,
    address: SurfaceAddress,
) -> str:
    if isinstance(address, StatisticalSurfaceAddress):
        addr_type_str = "sta"
    elif isinstance(address, SimulatedSurfaceAddress):
        addr_type_str = "sim"
    elif isinstance(address, ObservedSurfaceAddress):
        addr_type_str = "obs"

    addr_hash = hashlib.md5(  # nosec
        json.dumps(asdict(address), sort_keys=True).encode()
    ).hexdigest()

    return f"{provider_id}___{addr_type_str}___{address.name}___{address.attribute}___{addr_hash}"


def _diff_address_to_str(
    provider_id_a: str,
    address_a: SurfaceAddress,
    provider_id_b: str,
    address_b: SurfaceAddress,
) -> str:
    return (
        "diff~~~"
        + _address_to_str(provider_id_a, address_a)
        + "~~~"
        + _address_to_str(provider_id_b, address_b)
    )


def _calc_map_component_bounds_and_rot(
    surface: xtgeo.RegularSurface,
) -> Tuple[List[float], float]:
    surf_corners = surface.get_map_xycorners()
    rptx = surf_corners[2][0]
    rpty = surf_corners[2][1]
    min_x = math.inf
    max_x = -math.inf
    min_y = math.inf
    max_y = -math.inf
    angle = -surface.rotation * math.pi / 180
    for coord in surf_corners:
        xpos = coord[0]
        ypos = coord[1]
        x_rotated = (
            rptx + ((xpos - rptx) * math.cos(angle)) - ((ypos - rpty) * math.sin(angle))
        )
        y_rotated = (
            rpty + ((xpos - rptx) * math.sin(angle)) + ((ypos - rpty) * math.cos(angle))
        )
        min_x = min(min_x, x_rotated)
        max_x = max(max_x, x_rotated)
        min_y = min(min_y, y_rotated)
        max_y = max(max_y, y_rotated)

    bounds = [
        min_x,
        min_y,
        max_x,
        max_y,
    ]

    return bounds, surface.rotation
