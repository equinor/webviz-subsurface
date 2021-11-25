from io import BytesIO
import json
from pathlib import Path
from dataclasses import asdict
from typing import List
from urllib.parse import quote_plus, unquote_plus
from flask import send_file
from dash import Dash
import xtgeo
from webviz_config.common_cache import CACHE
import webviz_subsurface

from webviz_subsurface._components.deckgl_map.data_loaders.xtgeo_surface import (
    surface_to_rgba,
)

from .models.surface_set_model import SurfaceSetModel, SurfaceContext

from werkzeug.routing import BaseConverter


class SurfaceContextConverter(BaseConverter):
    """A custom converter used in a flask route to"""

    def to_python(self, value):
        if value == "UNDEF":
            return None
        return SurfaceContext(**json.loads(unquote_plus(value)))

    def to_url(self, surface_context: SurfaceContext = None):
        if surface_context is None:
            return "UNDEF"
        return quote_plus(json.dumps(asdict(surface_context)))


def deckgl_map_routes(app: Dash, surface_set_models: List[SurfaceSetModel]) -> None:
    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def _send_surface_as_png(surface_context: SurfaceContext = None):
        if not surface_context:
            surface = xtgeo.RegularSurface(ncol=1, nrow=1, xinc=1, yinc=1)
        else:
            ensemble = surface_context.ensemble
            surface = surface_set_models[ensemble].get_surface(surface_context)

        img_stream = surface_to_rgba(surface).read()
        return send_file(BytesIO(img_stream), mimetype="image/png")

    def _send_colormap(colormap: str = "seismic"):
        return send_file(
            Path(webviz_subsurface.__file__).parent
            / "_assets"
            / "colormaps"
            / f"{colormap}.png",
            mimetype="image/png",
        )

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def _send_well_data_as_json(hash: str):
        pass

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def _send_log_data_as_json(hash: str):
        pass

    app.server.view_functions["_send_surface_as_png"] = _send_surface_as_png
    app.server.view_functions["_send_colormap"] = _send_colormap
    app.server.view_functions["_send_well_data_as_json"] = _send_well_data_as_json
    app.server.view_functions["_send_log_data_as_json"] = _send_log_data_as_json
    app.server.url_map.converters["surface_context"] = SurfaceContextConverter
    app.server.add_url_rule(
        "/surface/<surface_context:surface_context>.png",
        view_func=_send_surface_as_png,
    )

    app.server.add_url_rule(
        "/colormaps/<colormap>.png",
        "_send_colormap",
    )
    app.server.add_url_rule(
        "/json/wells/<hash>.json",
        view_func=_send_well_data_as_json,
    )
    app.server.add_url_rule(
        "/json/logs/<hash>.json",
        view_func=_send_log_data_as_json,
    )
