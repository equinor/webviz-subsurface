from typing import List, Optional

from webviz_subsurface_components import (
    ExpressionInfo,
    VariableVectorMapInfo,
    VectorDefinition,
)

from webviz_subsurface._providers import VectorMetadata
from webviz_subsurface.plugins._simulation_time_series.types.provider_set import (
    ProviderSet,
)
from webviz_subsurface.plugins._simulation_time_series.utils.provider_set_utils import (
    create_calculated_unit_from_provider_set,
    create_vector_plot_titles_from_provider_set,
)

from ..mocks.ensemble_summary_provider_dummy import EnsembleSummaryProviderDummy

# *******************************************************************
#####################################################################
#
# CONFIGURE TESTDATA
#
#####################################################################
# *******************************************************************


class EnsembleSummaryProviderMock(EnsembleSummaryProviderDummy):
    """Ensemble summary provider mock for testing

    Note empty list returned in override methods, only to allow constructing
    ProviderSet objects!
    """

    ########################################
    #
    # Override methods
    #
    ########################################
    def vector_names(self) -> List[str]:
        """Return empty list only to allow constructing ProviderSet object"""
        return ["FGIT", "WGOR:A1", "WBHP:A1", "WOPT:A1"]

    def realizations(self) -> List[int]:
        """Return empty list only to allow constructing ProviderSet object"""
        return []

    def vector_metadata(self, vector_name: str) -> Optional[VectorMetadata]:
        # NOTE: All vector names below must be defined in vector_names() method as well!
        if vector_name == "FGIT":
            return VectorMetadata(
                unit="unit_1",
                is_total=False,
                is_rate=False,
                is_historical=False,
                keyword="FGIT",
                wgname=None,
                get_num=None,
            )
        if vector_name == "WGOR:A1":
            return VectorMetadata(
                unit="unit_2",
                is_total=False,
                is_rate=False,
                is_historical=False,
                keyword="A1",
                wgname=None,
                get_num=None,
            )
        if vector_name == "WBHP:A1":
            return VectorMetadata(
                unit="unit_3",
                is_total=False,
                is_rate=False,
                is_historical=False,
                keyword="A1",
                wgname=None,
                get_num=None,
            )
        if vector_name == "WOPT:A1":
            return VectorMetadata(
                unit="unit_4",
                is_total=False,
                is_rate=False,
                is_historical=False,
                keyword="A1",
                wgname=None,
                get_num=None,
            )
        return None


FIRST_TEST_EXPRESSION = ExpressionInfo(
    name="First Expression",
    expression="x+y",
    id="FirstId",
    variableVectorMap=[
        VariableVectorMapInfo(variableName="x", vectorName=["FGIT"]),
        VariableVectorMapInfo(variableName="y", vectorName=["WGOR:A1"]),
    ],
    isValid=True,
    isDeletable=False,
)

SECOND_TEST_EXPRESSION = ExpressionInfo(
    name="Second Expression",
    expression="x-y",
    id="SecondId",
    variableVectorMap=[
        VariableVectorMapInfo(variableName="x", vectorName=["FGIT"]),
        VariableVectorMapInfo(variableName="y", vectorName=["WBHP:A1"]),
    ],
    isValid=True,
    isDeletable=False,
)

THIRD_TEST_EXPRESSION = ExpressionInfo(
    name="Third Expression",
    expression="x/y",
    id="ThirdId",
    variableVectorMap=[
        VariableVectorMapInfo(variableName="x", vectorName=["WBHP:A1"]),
        VariableVectorMapInfo(variableName="y", vectorName=["WGOR:A1"]),
    ],
    isValid=True,
    isDeletable=False,
)

INVALID_TEST_EXPRESSION = ExpressionInfo(
    name="Invalid Expression",
    expression="invalid_function(x)",  # Invalid function
    id="InvalidId",
    variableVectorMap=[
        VariableVectorMapInfo(variableName="x", vectorName=["WBHP:A1"]),
    ],
    isValid=True,
    isDeletable=False,
)

TEST_PROVIDER_SET = ProviderSet({"First Provider": EnsembleSummaryProviderMock()})


# *******************************************************************
#####################################################################
#
# UNIT TESTS
#
#####################################################################
# *******************************************************************


def test_create_calculated_unit_from_provider_set() -> None:
    assert (
        create_calculated_unit_from_provider_set(
            FIRST_TEST_EXPRESSION, TEST_PROVIDER_SET
        )
        == "unit_1+unit_2"
    )
    assert (
        create_calculated_unit_from_provider_set(
            SECOND_TEST_EXPRESSION, TEST_PROVIDER_SET
        )
        == "unit_1-unit_3"
    )
    assert (
        create_calculated_unit_from_provider_set(
            THIRD_TEST_EXPRESSION, TEST_PROVIDER_SET
        )
        == "unit_3/unit_2"
    )
    assert (
        create_calculated_unit_from_provider_set(
            INVALID_TEST_EXPRESSION, TEST_PROVIDER_SET
        )
        is None
    )


def test_create_vector_plot_titles_from_provider_set() -> None:
    vector_names = ["FGIT", "WGOR:A1", "PER_DAY_WOPT:A1", "First Expression"]
    expressions = [FIRST_TEST_EXPRESSION]

    # Test WITHOUT user defined vector definitions
    expected_titles = {
        "FGIT": "Gas Injection Total [unit_1]",
        "WGOR:A1": "Gas-Oil Ratio, well A1 [unit_2]",
        "PER_DAY_WOPT:A1": "Average Oil Production Total Per day, well A1 [unit_4/DAY]",
        "First Expression": "First Expression [unit_1+unit_2]",
    }
    assert expected_titles == create_vector_plot_titles_from_provider_set(
        vector_names, expressions, TEST_PROVIDER_SET, {}
    )

    # Test WITH user defined vector definitions
    user_defined_definitions = {
        "FGIT": VectorDefinition(description="First Test title", type="field"),
        "WOPT": VectorDefinition(description="Second Test title", type="well"),
    }
    expected_titles = {
        "FGIT": "First Test title [unit_1]",
        "WGOR:A1": "Gas-Oil Ratio, well A1 [unit_2]",
        "PER_DAY_WOPT:A1": "Average Second Test title Per day, well A1 [unit_4/DAY]",
        "First Expression": "First Expression [unit_1+unit_2]",
    }

    assert expected_titles == create_vector_plot_titles_from_provider_set(
        vector_names, expressions, TEST_PROVIDER_SET, user_defined_definitions
    )
