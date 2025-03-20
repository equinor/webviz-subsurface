import json
import logging
from dataclasses import asdict, dataclass
from typing import Dict, Optional
from urllib.parse import quote

import flask
import geojson
import xtgeo
from dash import Dash

from .ensemble_polygon_provider import EnsemblePolygonProvider, PolygonsAddress

LOGGER = logging.getLogger(__name__)

_ROOT_URL_PATH = "/PolygonServer"

_POLYGONS_SERVER_INSTANCE: Optional["PolygonServer"] = None


@dataclass(frozen=True)
class QualifiedAddress:
    provider_id: str
    address: PolygonsAddress


class PolygonServer:
    def __init__(self, app: Dash) -> None:
        self._setup_url_rule(app)
        self._id_to_provider_dict: Dict[str, EnsemblePolygonProvider] = {}

    @staticmethod
    def instance(app: Dash) -> "PolygonServer":
        # pylint: disable=global-statement
        global _POLYGONS_SERVER_INSTANCE
        if not _POLYGONS_SERVER_INSTANCE:
            LOGGER.debug("Initializing PolygonServer instance")
            _POLYGONS_SERVER_INSTANCE = PolygonServer(app)

        return _POLYGONS_SERVER_INSTANCE

    def add_provider(self, provider: EnsemblePolygonProvider) -> None:
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
        polygons_address: PolygonsAddress,
    ) -> str:
        if not provider_id in self._id_to_provider_dict:
            raise ValueError("Could not find provider")

        url_path: str = (
            f"{_ROOT_URL_PATH}/{quote(provider_id)}"
            f"/{quote(json.dumps(asdict(polygons_address)))}"
        )

        return url_path

    def _setup_url_rule(self, app: Dash) -> None:
        @app.server.route(_ROOT_URL_PATH + "/<provider_id>/<polygons_address>")
        def _handle_polygons_request(
            provider_id: str,
            polygons_address: str,
        ) -> flask.Response:
            LOGGER.debug(
                f"Handling polygons_request: "
                f"full_polygons_address={polygons_address} "
            )

            polygons_geojson = None
            # try:

            address = PolygonsAddress(**json.loads(polygons_address))
            provider = self._id_to_provider_dict[provider_id]
            polygons = provider.get_polygons(address)
            if polygons is not None:
                polygons_geojson = _create_polygons_geojson(
                    polygons=polygons,
                )

            # except Exception as e:
            #     LOGGER.error("Error decoding polygons address")
            #     print(e)
            #     # flask.abort(404)
            featurecoll = (
                polygons_geojson
                if polygons_geojson is not None
                else {
                    "type": "FeatureCollection",
                    "features": [],
                }
            )

            return flask.Response(
                geojson.dumps(featurecoll), mimetype="application/geo+json"
            )


def _create_polygons_geojson(polygons: xtgeo.Polygons) -> Dict:
    feature_arr = []
    prop_style = {"color": [0, 0, 0, 255]}
    for name, polygon in polygons.dataframe.groupby("POLY_ID"):
        coords = [list(zip(polygon.X_UTME, polygon.Y_UTMN))]
        feature = geojson.Feature(
            geometry=geojson.Polygon(coords),
            properties={"name": f"id:{name}", **prop_style},
        )
        feature_arr.append(feature)
    return geojson.FeatureCollection(features=feature_arr)
