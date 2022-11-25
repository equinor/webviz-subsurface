from dataclasses import dataclass
from typing import List, Optional, Tuple, Union

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
from webviz_subsurface.plugins._co2_leakage._utilities.plume_extent import (
    truncate_surfaces,
)


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
) -> Tuple[Optional[SurfaceImageMeta], str]:
    if isinstance(address, TruncatedSurfaceAddress):
        return _publish_and_get_truncated_surface_metadata(server, provider, address)
    provider_id: str = provider.provider_id()
    qualified_address = QualifiedSurfaceAddress(provider_id, address)
    surf_meta = server.get_surface_metadata(qualified_address)
    if not surf_meta:
        # This means we need to compute the surface
        surface = provider.get_surface(address)
        if not surface:
            raise ValueError(f"Could not get surface for address: {address}")
        server.publish_surface(qualified_address, surface)
        surf_meta = server.get_surface_metadata(qualified_address)
    return surf_meta, server.encode_partial_url(qualified_address)


def _publish_and_get_truncated_surface_metadata(
    server: SurfaceImageServer,
    provider: EnsembleSurfaceProvider,
    address: TruncatedSurfaceAddress,
) -> Tuple[Optional[SurfaceImageMeta], str]:
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
    if surf_meta is None:
        surface = _generate_surface(provider, address)
        if surface is None:
            raise ValueError(f"Could not generate surface for address: {address}")
        server.publish_surface(qualified_address, surface)
        surf_meta = server.get_surface_metadata(qualified_address)
    return surf_meta, server.encode_partial_url(qualified_address)


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
