from webviz_subsurface._providers import VectorMetadata
from webviz_subsurface.plugins._simulation_time_series.utils.trace_line_shape import (
    get_simulation_line_shape,
)


def test_get_simulation_line_shape() -> None:
    total_vector_metadata = VectorMetadata(
        unit="M3",
        is_total=True,
        is_rate=False,
        is_historical=False,
        keyword="Test",
        wgname=None,
        get_num=None,
    )

    rate_vector_metadata = VectorMetadata(
        unit="M3/Day",
        is_total=False,
        is_rate=True,
        is_historical=False,
        keyword="Test rate",
        wgname=None,
        get_num=None,
    )

    fallthrough_vector_metadata = VectorMetadata(
        unit="M3/M3",
        is_total=False,
        is_rate=False,
        is_historical=False,
        keyword="Test fallthrough",
        wgname=None,
        get_num=None,
    )

    assert get_simulation_line_shape("Fallback", "PER_INTVL_vector", None) == "hv"
    assert get_simulation_line_shape("Fallback", "PER_DAY_vector", None) == "hv"
    assert get_simulation_line_shape("Fallback", "test_vector", None) == "Fallback"
    assert (
        get_simulation_line_shape("Fallback", "test_vector", total_vector_metadata)
        == "linear"
    )
    assert (
        get_simulation_line_shape("Fallback", "test_vector", rate_vector_metadata)
        == "vh"
    )
    assert (
        get_simulation_line_shape(
            "Fallback", "test_vector", fallthrough_vector_metadata
        )
        == "Fallback"
    )
