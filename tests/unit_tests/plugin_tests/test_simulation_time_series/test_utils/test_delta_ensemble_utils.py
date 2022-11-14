from typing import List

import pytest

from webviz_subsurface._utils.ensemble_summary_provider_set import (
    EnsembleSummaryProviderSet,
)

# pylint: disable=line-too-long
from webviz_subsurface.plugins._simulation_time_series._views._subplot_view._utils.delta_ensemble_utils import (
    DeltaEnsemble,
    create_delta_ensemble_name,
    create_delta_ensemble_name_dict,
    create_delta_ensemble_names,
    create_delta_ensemble_provider_pair,
    is_delta_ensemble_providers_in_provider_set,
)

from ....mocks.ensemble_summary_provider_dummy import EnsembleSummaryProviderDummy

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
    EnsembleSummaryProviderSet objects!
    """

    def __init__(self, name: str) -> None:
        super().__init__()
        self._name = name

    def get_name(self) -> str:
        return self._name

    ########################################
    #
    # Override methods
    #
    ########################################
    def vector_names(self) -> List[str]:
        """Return empty list only to allow constructing EnsembleSummaryProviderSet object"""
        return []

    def realizations(self) -> List[int]:
        """Return empty list only to allow constructing EnsembleSummaryProviderSet object"""
        return []


# *******************************************************************
#####################################################################
#
# UNIT TESTS
#
#####################################################################
# *******************************************************************


def test_create_delta_ensemble_name() -> None:
    assert (
        create_delta_ensemble_name(
            DeltaEnsemble(ensemble_a="first name", ensemble_b="second name")
        )
        == "(first name)-(second name)"
    )
    assert (
        create_delta_ensemble_name(
            DeltaEnsemble(ensemble_a="first-Name", ensemble_b="second-Name")
        )
        == "(first-Name)-(second-Name)"
    )
    assert (
        create_delta_ensemble_name(
            DeltaEnsemble(ensemble_a="ens-0", ensemble_b="ens-3")
        )
        == "(ens-0)-(ens-3)"
    )


def test_create_delta_ensemble_names() -> None:
    first_delta_ensemble = DeltaEnsemble(
        ensemble_a="first name", ensemble_b="second name"
    )
    second_delta_ensemble = DeltaEnsemble(
        ensemble_a="first-Name", ensemble_b="second-Name"
    )
    third_delta_ensemble = DeltaEnsemble(ensemble_a="ens-0", ensemble_b="ens-3")

    assert create_delta_ensemble_names(
        [first_delta_ensemble, second_delta_ensemble, third_delta_ensemble]
    ) == ["(first name)-(second name)", "(first-Name)-(second-Name)", "(ens-0)-(ens-3)"]


def test_create_delta_ensemble_name_dict() -> None:
    first_delta_ensemble = DeltaEnsemble(
        ensemble_a="first name", ensemble_b="second name"
    )
    second_delta_ensemble = DeltaEnsemble(
        ensemble_a="first-Name", ensemble_b="second-Name"
    )
    third_delta_ensemble = DeltaEnsemble(ensemble_a="ens-0", ensemble_b="ens-3")

    expected_delta_ensemble_name_dict = {
        "(first name)-(second name)": first_delta_ensemble,
        "(first-Name)-(second-Name)": second_delta_ensemble,
        "(ens-0)-(ens-3)": third_delta_ensemble,
    }

    assert (
        create_delta_ensemble_name_dict(
            [first_delta_ensemble, second_delta_ensemble, third_delta_ensemble]
        )
        == expected_delta_ensemble_name_dict
    )


def test_is_delta_ensemble_providers_in_provider_set() -> None:
    provider_set = EnsembleSummaryProviderSet(
        {
            "First provider": EnsembleSummaryProviderMock("First mock"),
            "Second provider": EnsembleSummaryProviderMock("Second mock"),
        }
    )

    valid_delta_ensemble = DeltaEnsemble(
        ensemble_a="First provider", ensemble_b="Second provider"
    )
    invalid_delta_ensemble = DeltaEnsemble(
        ensemble_a="First provider", ensemble_b="Third provider"
    )

    assert is_delta_ensemble_providers_in_provider_set(
        valid_delta_ensemble, provider_set
    )
    assert not is_delta_ensemble_providers_in_provider_set(
        invalid_delta_ensemble, provider_set
    )


def test_create_delta_ensemble_provider_pair() -> None:
    provider_set = EnsembleSummaryProviderSet(
        {
            "First provider": EnsembleSummaryProviderMock("First mock"),
            "Second provider": EnsembleSummaryProviderMock("Second mock"),
            "Third provider": EnsembleSummaryProviderMock(("Third mock")),
        }
    )

    first_delta_ensemble = DeltaEnsemble(
        ensemble_a="First provider", ensemble_b="Third provider"
    )
    second_delta_ensemble = DeltaEnsemble(
        ensemble_a="Third provider", ensemble_b="Second provider"
    )

    first_provider_pair = create_delta_ensemble_provider_pair(
        first_delta_ensemble, provider_set
    )
    second_provider_pair = create_delta_ensemble_provider_pair(
        second_delta_ensemble, provider_set
    )

    assert len(first_provider_pair) == 2
    ensemble_a = first_provider_pair[0]
    ensemble_b = first_provider_pair[1]
    if not isinstance(ensemble_a, EnsembleSummaryProviderMock):
        pytest.fail(
            f'Expected "{ensemble_a}" in second provider pair to be of type '
            "EnsembleSummaryProviderMock"
        )
    if not isinstance(ensemble_b, EnsembleSummaryProviderMock):
        pytest.fail(
            f'Expected "{ensemble_b}" in second provider pair to be of type '
            "EnsembleSummaryProviderMock"
        )
    assert ensemble_a.get_name() == "First mock"
    assert ensemble_b.get_name() == "Third mock"

    assert len(second_provider_pair) == 2
    ensemble_a = second_provider_pair[0]
    ensemble_b = second_provider_pair[1]
    if not isinstance(ensemble_a, EnsembleSummaryProviderMock):
        pytest.fail(
            f'Expected "{ensemble_a}" in second provider pair to be of type '
            "EnsembleSummaryProviderMock"
        )
    if not isinstance(ensemble_b, EnsembleSummaryProviderMock):
        pytest.fail(
            f'Expected "{ensemble_b}" in second provider pair to be of type '
            "EnsembleSummaryProviderMock"
        )
    assert ensemble_a.get_name() == "Third mock"
    assert ensemble_b.get_name() == "Second mock"


def test_create_delta_ensemble_provider_pair_invalid_ensemble() -> None:
    provider_set = EnsembleSummaryProviderSet(
        {
            "First provider": EnsembleSummaryProviderMock("First mock"),
            "Second provider": EnsembleSummaryProviderMock("Second mock"),
        }
    )

    # Expect ValueError when retrieveing ensemble_b is invalid
    with pytest.raises(ValueError):
        invalid_provider = "Invalid provider"
        invalid_provider_pair = DeltaEnsemble(
            ensemble_a="First provider", ensemble_b=invalid_provider
        )
        create_delta_ensemble_provider_pair(invalid_provider_pair, provider_set)
        pytest.fail(
            "Expected ValueError when creating delta ensemble provider pair, as ensemble b = "
            f'"{invalid_provider}" is not existing in provider set!'
        )
