import hashlib
import json
import warnings
from dataclasses import dataclass, replace
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import scipy
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
from webviz_subsurface.plugins._co2_migration._utilities.generic import (
    MapAttribute,
    MapType,
)

SCALE_DICT = {"kg": 0.001, "tons": 1, "M tons": 1e6}
_SURFACE_TRANSFORM_VERSION = "1.0"


@dataclass(frozen=True)
class SurfaceTransform:
    map_attribute: MapAttribute
    mass_unit: str
    visualization_threshold: Optional[float]


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


def _surface_cache_address(
    address: SurfaceAddress,
    transform: SurfaceTransform,
) -> SurfaceAddress:
    map_type = MapType[transform.map_attribute.name].value
    if map_type in ("PLUME", "MIGRATION_TIME"):
        return address

    transformation: Dict[str, Any] = {
        "version": _SURFACE_TRANSFORM_VERSION,
        "visualization_threshold": (
            transform.visualization_threshold
            if transform.visualization_threshold is not None
            and transform.visualization_threshold >= 0
            else None
        ),
    }
    if map_type == "MASS":
        transformation["mass_unit"] = transform.mass_unit

    digest = hashlib.sha256(
        json.dumps(transformation, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]
    return replace(
        address,
        attribute=f"{address.attribute}__co2migration_{digest}",
    )


def publish_and_get_surface_metadata(
    server: SurfaceImageServer,
    provider: EnsembleSurfaceProvider,
    address: Union[SurfaceAddress, TruncatedSurfaceAddress],
    transform: SurfaceTransform,
) -> Tuple[Optional[SurfaceImageMeta], Optional[str], Optional[Any]]:
    if isinstance(address, TruncatedSurfaceAddress):
        meta, partial_url = _publish_and_get_truncated_surface_metadata(
            server, provider, address
        )
        return meta, partial_url, None
    map_type = MapType[transform.map_attribute.name].value
    if map_type == "MIGRATION_TIME" and isinstance(address, StatisticalSurfaceAddress):
        meta, partial_url = _publish_and_get_statistical_time_surface_metadata(
            server,
            provider,
            address,
        )
        return meta, partial_url, None
    provider_id: str = provider.provider_id()
    qualified_address = QualifiedSurfaceAddress(
        provider_id,
        _surface_cache_address(
            address,
            transform,
        ),
    )
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

        if map_type == "MASS":
            surface.values = surface.values / SCALE_DICT[transform.mass_unit]
            summed_mass = np.ma.sum(surface.values)
        if (
            map_type not in ["PLUME", "MIGRATION_TIME"]
            and transform.visualization_threshold is not None
            and transform.visualization_threshold >= 0
        ):
            surface.operation(
                "elile",
                transform.visualization_threshold,
            )
        server.publish_surface(qualified_address, surface)
        surf_meta = server.get_surface_metadata(qualified_address)
    return surf_meta, server.encode_partial_url(qualified_address), summed_mass


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
    plume_count = _truncate_surfaces(surfaces, address.threshold, address.smoothing)
    template: xtgeo.RegularSurface = surfaces[0].copy()  # type: ignore
    template.values = plume_count
    template.values.mask = plume_count < 1e-4  # type: ignore
    return template


def _truncate_surfaces(
    surfaces: List[xtgeo.RegularSurface], threshold: float, smoothing: float
) -> np.ndarray:
    binary = [
        (
            np.where(np.isnan(s.values) | s.values.mask, 0.0, s.values) > threshold
        ).astype(float)
        for s in surfaces
    ]
    count = sum(binary)
    return scipy.ndimage.gaussian_filter(count, sigma=smoothing, mode="nearest")


def _publish_and_get_statistical_time_surface_metadata(
    server: SurfaceImageServer,
    provider: EnsembleSurfaceProvider,
    address: StatisticalSurfaceAddress,
) -> Tuple[Optional[SurfaceImageMeta], str]:
    qualified_address = QualifiedSurfaceAddress(
        provider.provider_id(),
        StatisticalSurfaceAddress(
            address.attribute,
            address.name,
            address.datestr,
            address.statistic,
            address.realizations,
        ),
    )
    surf_meta = server.get_surface_metadata(qualified_address)
    if surf_meta is None:
        surface = _generate_statisical_time_surface(provider, address)
        if surface is None:
            raise ValueError(f"Could not generate surface for address: {address}")
        server.publish_surface(qualified_address, surface)
        surf_meta = server.get_surface_metadata(qualified_address)
    return surf_meta, server.encode_partial_url(qualified_address)


def _generate_statisical_time_surface(
    provider: EnsembleSurfaceProvider,
    address: StatisticalSurfaceAddress,
) -> Optional[xtgeo.RegularSurface]:
    surfaces = [
        provider.get_surface(
            SimulatedSurfaceAddress(
                attribute=address.attribute,
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
    statistical_map = _statistics_on_time_map(surfaces, address.statistic)
    if statistical_map is None:
        return None
    template: xtgeo.RegularSurface = surfaces[0].copy()  # type: ignore
    template.values = statistical_map
    return template


# pylint: disable=too-many-return-statements
def _statistics_on_time_map(
    surfaces: List[xtgeo.RegularSurface],
    statistic: SurfaceStatistic,
) -> Optional[np.ndarray]:
    maps = np.zeros((len(surfaces), *surfaces[0].values.shape))
    for i, surface in enumerate(surfaces):
        maps[i, :, :] = surface.values
        masked = np.where(surface.values.mask)
        maps[i, masked[0], masked[1]] = np.inf
    if statistic == SurfaceStatistic.MEAN:
        return _turn_inf_to_nan(np.mean(maps, axis=0))
    if statistic == SurfaceStatistic.STDDEV:
        return _turn_inf_to_nan(np.std(maps, axis=0))
    if statistic == SurfaceStatistic.MINIMUM:
        return _turn_inf_to_nan(np.min(maps, axis=0))
    if statistic == SurfaceStatistic.MAXIMUM:
        return _turn_inf_to_nan(np.max(maps, axis=0))
    if statistic == SurfaceStatistic.P10:
        return _turn_inf_to_nan(np.percentile(maps, 10, axis=0))
    if statistic == SurfaceStatistic.P90:
        return _turn_inf_to_nan(np.percentile(maps, 90, axis=0))
    return None


def _turn_inf_to_nan(surface: np.ndarray) -> np.ndarray:
    surface[np.where(surface == np.inf)] = np.nan
    return surface
