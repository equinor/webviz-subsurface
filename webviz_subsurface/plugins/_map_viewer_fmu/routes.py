from io import BytesIO
from pathlib import Path
from typing import List

from flask import send_file
from dash import Dash
import xtgeo
from webviz_config.common_cache import CACHE
import webviz_subsurface

from webviz_subsurface._components.deckgl_map.data_loaders.xtgeo_surface import (
    surface_to_rgba,
)

from .models.surface_set_model import SurfaceSetModel, SurfaceContext


def deckgl_map_routes(app: Dash, surface_set_models: List[SurfaceSetModel]) -> None:
    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def _send_surface_as_png(hash: str):
        if hash == "UNDEF":
            surface = xtgeo.RegularSurface(ncol=1, nrow=1, xinc=1, yinc=1)
        else:
            surface_context = SurfaceContext.from_url(hash)
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
