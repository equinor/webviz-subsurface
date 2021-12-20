from typing import Callable, Dict, List, Tuple, Union
from pathlib import Path
import io
import orjson as json

from dataclasses import asdict
from urllib.parse import quote_plus, unquote_plus
from werkzeug.routing import BaseConverter

from flask import send_file
import xtgeo
from dash import Dash, Input, Output, State, no_update

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

import webviz_core_components as wcc
import webviz_subsurface_components as wsc

from ._make_rgba import surface_to_rgba


from ._layout import main_layout


class EnsembleSurfaceSendSurfaceAddress(WebvizPluginABC):
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

            surface_address_uri = quote_plus(
                json.dumps(
                    {
                        "__type__": surface_address.__class__.__name__,
                        "address": asdict(surface_address),
                    }
                )
            )

            layers[0][
                "image"
            ] = f"/{self.uuid('routes')}/surface/{surface_address_uri}.png"  # self.provider.get_url?
            return layers, bounds

    def set_routes(self, app):
        @app.server.route(f"/{self.uuid('routes')}/surface/<surface_address_uri>.png")
        def _send_surface_as_png(surface_address_uri):
            surface_address_payload = json.loads(unquote_plus(surface_address_uri))
            surface_address = None
            if surface_address_payload["__type__"] == "SimulatedSurfaceAddress":
                surface_address = SimulatedSurfaceAddress(
                    **surface_address_payload["address"]
                )
            if surface_address_payload["__type__"] == "StatisticalSurfaceAddress":
                surface_address = StatisticalSurfaceAddress(
                    **surface_address_payload["address"]
                )
            if not surface_address:
                surface = xtgeo.RegularSurface(ncol=1, nrow=1, xinc=1, yinc=1)
            else:

                surface = self.provider.get_surface(surface_address)

            img_stream = surface_to_rgba(surface)
            return send_file(io.BytesIO(img_stream), mimetype="image/png")
