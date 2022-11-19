from typing import Optional

from webviz_subsurface._providers import VectorMetadata

from .from_timeseries_cumulatives import is_per_interval_or_per_day_vector


def get_simulation_line_shape(
    line_shape_fallback: str,
    vector: str,
    vector_metadata: Optional[VectorMetadata] = None,
) -> str:
    """Get simulation time series line shape based on vector metadata"""
    if is_per_interval_or_per_day_vector(vector):
        # These custom calculated vectors are valid forwards in time.
        return "hv"

    if vector_metadata is None:
        return line_shape_fallback
    if vector_metadata.is_rate:
        # Eclipse rate vectors are valid backwards in time.
        return "vh"
    if vector_metadata.is_total:
        return "linear"
    return line_shape_fallback
