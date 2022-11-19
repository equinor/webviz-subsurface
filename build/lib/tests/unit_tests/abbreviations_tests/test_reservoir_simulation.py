from webviz_subsurface_components import VectorDefinition, VectorDefinitions

from webviz_subsurface._abbreviations.reservoir_simulation import (
    simulation_vector_description,
)


def test_simulation_vector_description_existing_vector() -> None:
    # Verify test vector exist in VectorDefinitions
    assert "WOPT" in VectorDefinitions

    # Test WITHOUT vector definitions argument
    assert simulation_vector_description("WOPT:A1") == "Oil Production Total, well A1"
    assert (
        simulation_vector_description("PER_DAY_WOPT:A1")
        == "Average Oil Production Total Per day, well A1"
    )
    assert (
        simulation_vector_description("PER_INTVL_WOPT:A1")
        == "Interval Oil Production Total, well A1"
    )
    assert (
        simulation_vector_description("AVG_WOPT:A1")
        == "Average Oil Production Total, well A1"
    )
    assert (
        simulation_vector_description("INTVL_WOPT:A1")
        == "Interval Oil Production Total, well A1"
    )

    # Test WITH vector definitions argument
    vector_definitions = {
        "WOPT": VectorDefinition(type="well", description="Test Description"),
    }
    assert (
        simulation_vector_description("WOPT:A1", vector_definitions)
        == "Test Description, well A1"
    )
    assert (
        simulation_vector_description("PER_DAY_WOPT:A1", vector_definitions)
        == "Average Test Description Per day, well A1"
    )
    assert (
        simulation_vector_description("PER_INTVL_WOPT:A1", vector_definitions)
        == "Interval Test Description, well A1"
    )
    assert (
        simulation_vector_description("AVG_WOPT:A1", vector_definitions)
        == "Average Test Description, well A1"
    )
    assert (
        simulation_vector_description("INTVL_WOPT:A1", vector_definitions)
        == "Interval Test Description, well A1"
    )


def test_simulation_vector_description_non_existing_vector() -> None:
    # Verify test vector does not exist in VectorDefinitions
    assert "Custom" not in VectorDefinitions

    # Test WITHOUT vector definitions argument
    assert simulation_vector_description("Custom:A1") == "Custom:A1"
    assert (
        simulation_vector_description("PER_DAY_Custom:A1")
        == "Average Custom:A1 Per day"
    )
    assert simulation_vector_description("PER_INTVL_Custom:A1") == "Interval Custom:A1"
    assert simulation_vector_description("AVG_Custom:A1") == "Average Custom:A1"
    assert simulation_vector_description("INTVL_Custom:A1") == "Interval Custom:A1"

    # Test WITH vector definitions argument
    vector_definitions = {
        "Custom": VectorDefinition(type="field", description="Custom Description"),
    }
    assert (
        simulation_vector_description("Custom:A1", vector_definitions)
        == "Custom Description, field A1"
    )
    assert (
        simulation_vector_description("PER_DAY_Custom:A1", vector_definitions)
        == "Average Custom Description Per day, field A1"
    )
    assert (
        simulation_vector_description("PER_INTVL_Custom:A1", vector_definitions)
        == "Interval Custom Description, field A1"
    )
    assert (
        simulation_vector_description("AVG_Custom:A1", vector_definitions)
        == "Average Custom Description, field A1"
    )
    assert (
        simulation_vector_description("INTVL_Custom:A1", vector_definitions)
        == "Interval Custom Description, field A1"
    )
