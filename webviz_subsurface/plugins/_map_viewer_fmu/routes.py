from io import BytesIO
from pathlib import Path
from typing import List

from flask import send_file
from dash import Dash

from webviz_config.common_cache import CACHE
import webviz_subsurface

from .models import SurfaceSetModel
from .utils.surface_utils import surface_context_from_url, surface_to_rgba


def deckgl_map_routes(app: Dash, surface_set_models: List[SurfaceSetModel]) -> None:
    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def _send_surface_as_png(hash: str):
        surface_context = surface_context_from_url(hash)
        ensemble = surface_context.ensemble
        surface = surface_set_models[ensemble].get_surface(surface_context)
        img_stream = surface_to_rgba(surface).read()
        return send_file(BytesIO(img_stream), mimetype="image/png")

    def _send_colormap(colormap="seismic"):
        return send_file(
            Path(webviz_subsurface.__file__).parent
            / "_assets"
            / "colormaps"
            / f"{colormap}.png",
            mimetype="image/png",
        )

    app.server.view_functions["_send_surface_as_png"] = _send_surface_as_png
    app.server.view_functions["_send_colormap"] = _send_colormap

    app.server.add_url_rule(
        "/surface/<hash>.png",
        view_func=_send_surface_as_png,
    )

    app.server.add_url_rule(
        "/colormaps/<colormap>.png",
        "_send_colormap",
    )
