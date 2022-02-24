import json
import logging
from dataclasses import asdict, dataclass
from typing import Dict, Optional
from urllib.parse import quote

import flask
import geojson
import xtgeo
from dash import Dash

from .ensemble_fault_polygons_provider import (
    EnsembleFaultPolygonsProvider,
    FaultPolygonsAddress,
)

LOGGER = logging.getLogger(__name__)

_ROOT_URL_PATH = "/FaultPolygonsServer"

_FAULT_POLYGONS_SERVER_INSTANCE: Optional["FaultPolygonsServer"] = None


@dataclass(frozen=True)
class QualifiedAddress:
    provider_id: str
    address: FaultPolygonsAddress


class FaultPolygonsServer:
    def __init__(self, app: Dash) -> None:

        self._setup_url_rule(app)
        self._id_to_provider_dict: Dict[str, EnsembleFaultPolygonsProvider] = {}

    @staticmethod
    def instance(app: Dash) -> "FaultPolygonsServer":
        # pylint: disable=global-statement
        global _FAULT_POLYGONS_SERVER_INSTANCE
        if not _FAULT_POLYGONS_SERVER_INSTANCE:
            LOGGER.debug("Initializing FaultPolygonsServer instance")
            _FAULT_POLYGONS_SERVER_INSTANCE = FaultPolygonsServer(app)

        return _FAULT_POLYGONS_SERVER_INSTANCE

    def add_provider(self, provider: EnsembleFaultPolygonsProvider) -> None:

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

    def encode_partial_url(
        self,
        provider_id: str,
        fault_polygons_address: FaultPolygonsAddress,
    ) -> str:
        if not provider_id in self._id_to_provider_dict:
            raise ValueError("Could not find provider")

        url_path: str = (
            f"{_ROOT_URL_PATH}/{quote(provider_id)}"
            f"/{quote(json.dumps(asdict(fault_polygons_address)))}"
        )

        return url_path

    def _setup_url_rule(self, app: Dash) -> None:
        @app.server.route(_ROOT_URL_PATH + "/<provider_id>/<fault_polygons_address>")
        def _handle_fault_polygons_request(
            provider_id: str,
            fault_polygons_address: str,
        ) -> flask.Response:
            LOGGER.debug(
                f"Handling fault_polygons_request: "
                f"full_fault_polygons_address={fault_polygons_address} "
            )

            fault_polygons_geojson = None
            # try:

            address = FaultPolygonsAddress(**json.loads(fault_polygons_address))
            provider = self._id_to_provider_dict[provider_id]
            fault_polygons = provider.get_fault_polygons(address)
            if fault_polygons is not None:
                fault_polygons_geojson = _create_fault_polygons_geojson(
                    polygons=fault_polygons
                )

            # except Exception as e:
            #     LOGGER.error("Error decoding fault polygons address")
            #     print(e)
            #     # flask.abort(404)
            featurecoll = (
                fault_polygons_geojson
                if fault_polygons_geojson is not None
                else {
                    "type": "FeatureCollection",
                    "features": [],
                }
            )

            return flask.Response(
                geojson.dumps(featurecoll), mimetype="application/geo+json"
            )


def _create_fault_polygons_geojson(polygons: xtgeo.Polygons) -> Dict:
    feature_arr = []
    for name, polygon in polygons.dataframe.groupby("POLY_ID"):
        coords = [list(zip(polygon.X_UTME, polygon.Y_UTMN))]
        feature = geojson.Feature(
            geometry=geojson.Polygon(coords),
            properties={"name": f"id:{name}", "color": [0, 0, 0, 255]},
        )
        feature_arr.append(feature)
    return geojson.FeatureCollection(features=feature_arr)
