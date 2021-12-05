# pylint: disable=all
# type: ignore

import json
from dataclasses import asdict
from io import BytesIO
from pathlib import Path
from typing import List
from urllib.parse import quote_plus, unquote_plus

import xtgeo
from dash import Dash
from flask import send_file
from webviz_config.common_cache import CACHE
from werkzeug.routing import BaseConverter

import webviz_subsurface
from webviz_subsurface._components.deckgl_map.providers.xtgeo import (
    WellLogToJson,
    WellToJson,
    surface_to_rgba,
)
from webviz_subsurface._models.well_set_model import WellSetModel

from .models.surface_set_model import SurfaceSetModel
from .types import LogContext, SurfaceContext, WellsContext


class SurfaceContextConverter(BaseConverter):
    """A custom converter used in a flask route to convert a SurfaceContext to/from an url for use
    in the DeckGLMap layer prop"""

    def to_python(self, value):
        if value == "UNDEF":
            return None
        return SurfaceContext(**json.loads(unquote_plus(value)))

    def to_url(self, surface_context: SurfaceContext = None):
        if surface_context is None:
            return "UNDEF"
        return quote_plus(json.dumps(asdict(surface_context)))


class WellsContextConverter(BaseConverter):
    """A custom converter used in a flask route to provide a list of wells for use in the DeckGLMap prop"""

    def to_python(self, value):
        if value == "UNDEF":
            return None
        return WellsContext(**json.loads(unquote_plus(value)))

    def to_url(self, wells_context: WellsContext = None):
        if wells_context is None:
            return "UNDEF"
        return quote_plus(json.dumps(asdict(wells_context)))


class LogsContextConverter(BaseConverter):
    """A custom converter used in a flask route to provide a log name for use in the DeckGLMap prop"""

    def to_python(self, value):
        if value == "UNDEF":
            return None
        return LogContext(**json.loads(unquote_plus(value)))

    def to_url(self, logs_context: LogContext = None):
        if logs_context is None:
            return "UNDEF"
        return quote_plus(json.dumps(asdict(logs_context)))


# class RGBARouter:
#     class Converter(BaseConverter):
#         """A custom converter used in a flask route to convert a SurfaceContext to/from an url for use
#         in the DeckGLMap layer prop"""

#         def to_python(self, value):
#             if value == "UNDEF":
#                 return None
#             return SurfaceContext(**json.loads(unquote_plus(value)))

#         def to_url(self, surface_context: SurfaceContext = None):
#             if surface_context is None:
#                 return "UNDEF"
#             return quote_plus(json.dumps(asdict(surface_context)))

#     def __init__(self, app, surface_set_models: List[SurfaceSetModel]):
#         self.surface_set_models = surface_set_models
#         print(self.__class__.__name__)
#         app.server.view_functions["test"] = self.endpoint
#         app.server.url_map.converters["surface_context"] = RGBARouter.Converter
#         app.server.add_url_rule(
#             f"/surface/<surface_context:surface_context>.png",
#             view_func=self.endpoint,
#         )

#     def endpoint(self, surface_context: SurfaceContext = None):
#         if not surface_context:
#             surface = xtgeo.RegularSurface(ncol=1, nrow=1, xinc=1, yinc=1)
#         else:
#             ensemble = surface_context.ensemble
#             surface = self.surface_set_models[ensemble].get_surface(surface_context)

#         img_stream = surface_to_rgba(surface).read()
#         return send_file(BytesIO(img_stream), mimetype="image/png")


def deckgl_map_routes(
    app: Dash,
    surface_set_models: List[SurfaceSetModel],
    well_set_model: WellSetModel = None,
) -> None:
    """Functions that are executed when the flask endpoint is triggered"""

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

    app.server.view_functions["_send_surface_as_png"] = _send_surface_as_png
    app.server.view_functions["_send_colormap"] = _send_colormap
    app.server.url_map.converters["surface_context"] = SurfaceContextConverter
    app.server.add_url_rule(
        "/surface/<surface_context:surface_context>.png",
        view_func=_send_surface_as_png,
    )

    app.server.add_url_rule(
        "/colormaps/<colormap>.png",
        "_send_colormap",
    )

    if well_set_model is not None:

        @CACHE.memoize(timeout=CACHE.TIMEOUT)
        def _send_well_data_as_json(wells_context: WellsContext):
            if not wells_context:
                return {}

            well_data = WellToJson(
                wells=[
                    well_set_model.get_well(well) for well in wells_context.well_names
                ]
            )
            return well_data

        @CACHE.memoize(timeout=CACHE.TIMEOUT)
        def _send_log_data_as_json(logs_context: LogContext):
            pass

        app.server.view_functions["_send_well_data_as_json"] = _send_well_data_as_json
        app.server.view_functions["_send_log_data_as_json"] = _send_log_data_as_json

        app.server.url_map.converters["wells_context"] = WellsContextConverter
        app.server.url_map.converters["logs_context"] = LogsContextConverter

        app.server.add_url_rule(
            "/json/wells/<wells_context:wells_context>.json",
            view_func=_send_well_data_as_json,
        )
        app.server.add_url_rule(
            "/json/logs/<logs_context:logs_context>.json",
            view_func=_send_log_data_as_json,
        )
