from typing import Dict, List, Optional

from webviz_subsurface._providers import (
    EnsembleFaultPolygonsProviderFactory,
    FaultPolygonsServer,
    SimulatedFaultPolygonsAddress,
)


class FaultPolygonsHandler:
    def __init__(
        self,
        server: FaultPolygonsServer,
        ensemble_path: str,
        map_surface_names_to_fault_polygons: Dict[str, str],
        fault_polygon_attribute: str,
    ) -> None:
        self._server = server
        polygon_provider_factory = EnsembleFaultPolygonsProviderFactory.instance()
        self._provider = (
            polygon_provider_factory.create_from_ensemble_fault_polygons_files(
                ensemble_path
            )
        )
        server.add_provider(self._provider)
        self._map_surface_names_to_fault_polygons = map_surface_names_to_fault_polygons
        self._fault_polygon_attribute = fault_polygon_attribute

    def extract_fault_polygon_url(
        self,
        polygon_name: str,
        realization: List[int],
    ) -> Optional[str]:
        if polygon_name is None:
            return None
        if len(realization) == 0:
            return None
        # NB! This always returns the url corresponding to the first realization
        address = SimulatedFaultPolygonsAddress(
            attribute=self._fault_polygon_attribute,
            name=self._map_surface_names_to_fault_polygons.get(
                polygon_name, polygon_name
            ),
            realization=realization[0],
        )
        return self._server.encode_partial_url(
            provider_id=self._provider.provider_id(),
            fault_polygons_address=address,
        )
