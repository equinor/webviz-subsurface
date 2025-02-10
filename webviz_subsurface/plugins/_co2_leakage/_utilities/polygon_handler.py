from typing import List, Optional

from webviz_subsurface._providers.ensemble_polygon_provider import (
    EnsemblePolygonProviderFactory,
    PolygonServer,
)
from webviz_subsurface._providers.ensemble_polygon_provider.ensemble_polygon_provider import (
    PolygonsAddress,
)
from webviz_subsurface.plugins._co2_leakage._utilities.generic import BoundarySettings


class PolygonHandler:
    def __init__(
        self,
        server: PolygonServer,
        ensemble_path: str,
        boundary_options: BoundarySettings,
    ) -> None:
        self._server = server
        self._attribute = boundary_options["attribute"]
        self._hazardous_name = boundary_options["hazardous_name"]
        self._containment_name = boundary_options["containment_name"]
        polygon_provider_factory = EnsemblePolygonProviderFactory.instance()
        self._provider = polygon_provider_factory.create_from_ensemble_polygon_files(
            ensemble_path,
            boundary_options["polygon_file_pattern"],
        )
        server.add_provider(self._provider)

    def extract_hazardous_poly_url(self, realization: List[int]) -> Optional[str]:
        return self._extract_polygon_url(
            self._hazardous_name, self._attribute, realization
        )

    def extract_containment_poly_url(self, realization: List[int]) -> Optional[str]:
        return self._extract_polygon_url(
            self._containment_name, self._attribute, realization
        )

    def _extract_polygon_url(
        self,
        name: str,
        attribute: str,
        realization: List[int],
    ) -> Optional[str]:
        if attribute is None:
            return None
        if len(realization) == 0:
            return None
        # NB! This always returns the url corresponding to the first realization
        address = PolygonsAddress(
            attribute=attribute,
            name=name,
            realization=realization[0],
        )
        return self._server.encode_partial_url(
            provider_id=self._provider.provider_id(),
            polygons_address=address,
        )
