from dataclasses import dataclass

from .ensemble_surface_provider import SurfaceAddress


@dataclass(frozen=True)
class QualifiedSurfaceAddress:
    provider_id: str
    address: SurfaceAddress


@dataclass(frozen=True)
class QualifiedDiffSurfaceAddress:
    provider_id_a: str
    address_a: SurfaceAddress
    provider_id_b: str
    address_b: SurfaceAddress
