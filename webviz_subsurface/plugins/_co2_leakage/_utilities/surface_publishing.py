import warnings
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import xtgeo

from webviz_subsurface._providers import (
    EnsembleSurfaceProvider,
    QualifiedSurfaceAddress,
    SimulatedSurfaceAddress,
    StatisticalSurfaceAddress,
    SurfaceAddress,
    SurfaceImageMeta,
    SurfaceImageServer,
)
from webviz_subsurface._providers.ensemble_surface_provider.ensemble_surface_provider import (
    SurfaceStatistic,
)
from webviz_subsurface.plugins._co2_leakage._utilities.generic import MapAttribute
from webviz_subsurface.plugins._co2_leakage._utilities.plume_extent import (
    truncate_surfaces,
)

SCALE_DICT = {"kg": 1, "tons": 1000, "M tons": 1000000}


@dataclass
class TruncatedSurfaceAddress:
    name: str
    datestr: str
    realizations: List[int]
    basis_attribute: str
    threshold: float
    smoothing: float

    @property
    def attribute(self) -> str:
        return f"Truncated_{self.basis_attribute}_{self.threshold}_{self.smoothing}"


def publish_and_get_surface_metadata(
    server: SurfaceImageServer,
    provider: EnsembleSurfaceProvider,
    address: Union[SurfaceAddress, TruncatedSurfaceAddress],
    visualization_info: Dict[str, Any],
    map_attribute_names: Dict[MapAttribute, str],
) -> Tuple[Optional[SurfaceImageMeta], Optional[str], Optional[Any]]:
    if isinstance(address, TruncatedSurfaceAddress):
        return _publish_and_get_truncated_surface_metadata(server, provider, address)
    provider_id: str = provider.provider_id()
    qualified_address = QualifiedSurfaceAddress(provider_id, address)
    surf_meta = server.get_surface_metadata(qualified_address)
    summed_mass = None
    if not surf_meta:
        # This means we need to compute the surface
        try:
            surface = provider.get_surface(address)
        except ValueError:
            surface = None
        if not surface:
            warnings.warn(f"Could not find surface file with properties: {address}")
            return None, None, None
        if address.attribute in [
            map_attribute_names[MapAttribute.MASS],
            map_attribute_names[MapAttribute.FREE],
            map_attribute_names[MapAttribute.DISSOLVED],
        ]:
            surface.values = surface.values / SCALE_DICT[visualization_info["unit"]]
        summed_mass = np.ma.sum(surface.values)
        if (
            address.attribute
            not in [
                map_attribute_names[MapAttribute.MIGRATION_TIME_SGAS],
                map_attribute_names[MapAttribute.MIGRATION_TIME_AMFG],
            ]
            and visualization_info["threshold"] >= 0
        ):
            surface.operation("elile", visualization_info["threshold"])
        server.publish_surface(qualified_address, surface)
        surf_meta = server.get_surface_metadata(qualified_address)
    return surf_meta, server.encode_partial_url(qualified_address), summed_mass


def _publish_and_get_truncated_surface_metadata(
    server: SurfaceImageServer,
    provider: EnsembleSurfaceProvider,
    address: TruncatedSurfaceAddress,
) -> Tuple[Optional[SurfaceImageMeta], str, Optional[Any]]:
    qualified_address = QualifiedSurfaceAddress(
        provider.provider_id(),
        # TODO: Should probably use a dedicated address type for this. Statistical surface
        #  is the closest, as it allows including a list of realizations. However, it is
        #  perhaps not very "statistical", and the provided SurfaceStatistic is not
        #  appropriate here.
        StatisticalSurfaceAddress(
            address.attribute,
            address.name,
            address.datestr,
            SurfaceStatistic.MEAN,
            address.realizations,
        ),
    )
    surf_meta = server.get_surface_metadata(qualified_address)
    summed_mass = None
    if surf_meta is None:
        surface = _generate_surface(provider, address)
        if surface is None:
            raise ValueError(f"Could not generate surface for address: {address}")
        summed_mass = np.ma.sum(surface.values)
        server.publish_surface(qualified_address, surface)
        surf_meta = server.get_surface_metadata(qualified_address)
    return surf_meta, server.encode_partial_url(qualified_address), summed_mass


def _generate_surface(
    provider: EnsembleSurfaceProvider,
    address: TruncatedSurfaceAddress,
) -> Optional[xtgeo.RegularSurface]:
    surfaces = [
        provider.get_surface(
            SimulatedSurfaceAddress(
                attribute=address.basis_attribute,
                name=address.name,
                datestr=address.datestr,
                realization=r,
            )
        )
        for r in address.realizations
    ]
    surfaces = [s for s in surfaces if s is not None]
    if len(surfaces) == 0:
        return None
    plume_count = truncate_surfaces(surfaces, address.threshold, address.smoothing)
    template: xtgeo.RegularSurface = surfaces[0].copy()  # type: ignore
    template.values = plume_count
    template.values.mask = plume_count < 1e-4  # type: ignore
    return template
