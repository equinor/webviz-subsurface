from typing import Dict

import pytest

from webviz_subsurface._providers.ensemble_summary_provider.ensemble_summary_provider import (
    EnsembleSummaryProvider,
    VectorMetadata,
)
from webviz_subsurface._utils.ensemble_summary_provider_set import (
    EnsembleSummaryProviderSet,
)

from .mocks.ensemble_summary_provider_mock import EnsembleSummaryProviderMock

TEST_PROVIDER_DICT: Dict[str, EnsembleSummaryProvider] = {
    "First provider": EnsembleSummaryProviderMock.create_mock_with_first_dataset(),
    "Second provider": EnsembleSummaryProviderMock.create_mock_with_second_dataset(),
    "Third provider": EnsembleSummaryProviderMock.create_mock_with_third_dataset(),
}

TEST_INCONSISTENT_PROVIDER_DICT: Dict[str, EnsembleSummaryProvider] = {
    "First provider": EnsembleSummaryProviderMock.create_mock_with_first_dataset(),
    "Third provider": EnsembleSummaryProviderMock.create_mock_with_third_dataset(),
    "Inconsistent provider": EnsembleSummaryProviderMock.create_mock_with_inconsistent_dataset(),
}


def test_verify_consistent_vector_metadata() -> None:
    consistent_provider_set = EnsembleSummaryProviderSet(TEST_PROVIDER_DICT)
    inconsistent_provider_set = EnsembleSummaryProviderSet(
        TEST_INCONSISTENT_PROVIDER_DICT
    )

    # Expect no ValueError when verifying
    try:
        consistent_provider_set.verify_consistent_vector_metadata()
    except ValueError as err:
        pytest.fail(
            f"Expected successful validation for consistent_metadata_set. Exception: {err}"
        )

    # Expect ValueError when verifying
    with pytest.raises(ValueError):
        inconsistent_provider_set.verify_consistent_vector_metadata()
        pytest.fail(
            "Expected unsuccessful verification of consistent vector metadata for "
            "inconsistent_metadata_set"
        )


def test_create_union_of_vector_names_from_providers() -> None:
    # NOTE: Use explicit type annotation for EnsembleSummaryProviderMock as Dict is invariant.
    # See: https://mypy.readthedocs.io/en/latest/common_issues.html#variance
    provider_dict: Dict[str, EnsembleSummaryProvider] = {
        "First provider": EnsembleSummaryProviderMock.create_mock_with_first_dataset(),
        "Second provider": EnsembleSummaryProviderMock.create_mock_with_second_dataset(),
    }
    provider_set = EnsembleSummaryProviderSet(provider_dict)

    # Vector names from first and second mock - without duplicates sorted alphabetically
    expected_vector_names = [
        "FGIR",
        "WBHP:A1",
        "WBHP:A2",
        "WGOR:A1",
        "WGOR:A2",
        "WOPR:A2",
        "WOPT:A1",
        "WOPT:A2",
        "WWCT:A1",
        "WWCT:A2",
    ]

    # pylint: disable = protected-access
    created_vector_names = provider_set._create_union_of_vector_names_from_providers(
        list(provider_dict.values())
    )

    assert created_vector_names == expected_vector_names


def test_create_union_of_realizations_from_providers() -> None:
    # NOTE: Use explicit type annotation for EnsembleSummaryProviderMock as Dict is invariant.
    # See: https://mypy.readthedocs.io/en/latest/common_issues.html#variance
    provider_dict: Dict[str, EnsembleSummaryProvider] = {
        "First provider": EnsembleSummaryProviderMock.create_mock_with_first_dataset(),
        "Second provider": EnsembleSummaryProviderMock.create_mock_with_second_dataset(),
    }
    provider_set = EnsembleSummaryProviderSet(provider_dict)

    # Realizations from first and second mock
    expected_realizations = [1, 2, 3, 4, 5, 8]

    # pylint: disable = protected-access
    created_realizations = provider_set._create_union_of_realizations_from_providers(
        list(provider_dict.values())
    )

    assert created_realizations == expected_realizations


def test_items() -> None:
    provider_set = EnsembleSummaryProviderSet(TEST_PROVIDER_DICT)
    assert provider_set.items() == TEST_PROVIDER_DICT.items()


def test_names() -> None:
    provider_set = EnsembleSummaryProviderSet(TEST_PROVIDER_DICT)
    assert provider_set.provider_names() == list(TEST_PROVIDER_DICT.keys())


def test_provider() -> None:
    provider_set = EnsembleSummaryProviderSet(TEST_PROVIDER_DICT)

    first_provider = provider_set.provider("First provider")
    second_provider = provider_set.provider("Second provider")
    third_provider = provider_set.provider("Third provider")
    if not isinstance(first_provider, EnsembleSummaryProviderMock):
        pytest.fail(
            f'Expected first provider "{first_provider}" to be type EnsembleSummaryProviderMock'
        )
    if not isinstance(second_provider, EnsembleSummaryProviderMock):
        pytest.fail(
            f'Expected second provider "{second_provider}" to be type EnsembleSummaryProviderMock'
        )
    if not isinstance(third_provider, EnsembleSummaryProviderMock):
        pytest.fail(
            f'Expected third provider "{third_provider}" to be type EnsembleSummaryProviderMock'
        )

    assert first_provider.get_dataset_name() == "First dataset"
    assert second_provider.get_dataset_name() == "Second dataset"
    assert third_provider.get_dataset_name() == "Third dataset"

    # Expect ValueError when getting invalid provider name
    with pytest.raises(ValueError):
        name = "Invalid Provider"
        provider_set.provider(name)
        pytest.fail(
            f'Expected getting provider "{name}" to fail, as it is not among provider names in set!'
        )


def test_all_providers() -> None:
    provider_set = EnsembleSummaryProviderSet(TEST_PROVIDER_DICT)
    all_providers = provider_set.all_providers()

    assert len(all_providers) == 3
    first_provider = all_providers[0]
    second_provider = all_providers[1]
    third_provider = all_providers[2]
    if not isinstance(first_provider, EnsembleSummaryProviderMock):
        pytest.fail(
            f'Expected first provider "{first_provider}" to be type EnsembleSummaryProviderMock'
        )
    if not isinstance(second_provider, EnsembleSummaryProviderMock):
        pytest.fail(
            f'Expected second provider "{second_provider}" to be type EnsembleSummaryProviderMock'
        )
    if not isinstance(third_provider, EnsembleSummaryProviderMock):
        pytest.fail(
            f'Expected third provider "{third_provider}" to be type EnsembleSummaryProviderMock'
        )

    assert first_provider.get_dataset_name() == "First dataset"
    assert second_provider.get_dataset_name() == "Second dataset"
    assert third_provider.get_dataset_name() == "Third dataset"


def test_all_realizations() -> None:
    provider_set = EnsembleSummaryProviderSet(TEST_PROVIDER_DICT)
    expected_realizations = [1, 2, 3, 4, 5, 7, 8]

    assert provider_set.all_realizations() == expected_realizations


def test_all_vector_names() -> None:
    provider_set = EnsembleSummaryProviderSet(TEST_PROVIDER_DICT)

    # Vector names from first, second and third mock - without duplicates sorted alphabetically
    expected_vector_names = [
        "FGIR",
        "FGIT",
        "WBHP:A1",
        "WBHP:A2",
        "WGOR:A1",
        "WGOR:A2",
        "WOPR:A1",
        "WOPR:A2",
        "WOPT:A1",
        "WOPT:A2",
        "WWCT:A1",
        "WWCT:A2",
    ]

    assert provider_set.all_vector_names() == expected_vector_names


def test_vector_metadata() -> None:
    provider_set = EnsembleSummaryProviderSet(TEST_PROVIDER_DICT)

    first_expected_metadata = VectorMetadata(
        unit="SM3/SM3",
        is_total=False,
        is_rate=True,
        is_historical=False,
        keyword="WGOR",
        wgname="A1",
        get_num=6,
    )

    second_expected_metadata = VectorMetadata(
        unit="",
        is_total=False,
        is_rate=True,
        is_historical=False,
        keyword="WWCT",
        wgname="A1",
        get_num=6,
    )

    third_expected_metadata = VectorMetadata(
        unit="SM3",
        is_total=True,
        is_rate=False,
        is_historical=False,
        keyword="FGIT",
        wgname=None,
        get_num=0,
    )

    assert provider_set.vector_metadata("WGOR:A1") == first_expected_metadata
    assert provider_set.vector_metadata("WWCT:A1") == second_expected_metadata
    assert provider_set.vector_metadata("FGIT") == third_expected_metadata
    assert provider_set.vector_metadata("Invalid Vector") is None


def test_vector_metadata_order() -> None:
    """The metadata returns first existing metadata, thereby inconsistent metadata
    will affect result based on the order of the providers in set.
    """

    # NOTE: Use explicit type annotation for EnsembleSummaryProviderMock as Dict is invariant.
    # See: https://mypy.readthedocs.io/en/latest/common_issues.html#variance
    first_provider_dict: Dict[str, EnsembleSummaryProvider] = {
        "First": EnsembleSummaryProviderMock.create_mock_with_first_dataset(),
        "Inconsistent": EnsembleSummaryProviderMock.create_mock_with_inconsistent_dataset(),
    }
    second_provider_dict: Dict[str, EnsembleSummaryProvider] = {
        "Inconsistent": EnsembleSummaryProviderMock.create_mock_with_inconsistent_dataset(),
        "First": EnsembleSummaryProviderMock.create_mock_with_first_dataset(),
    }
    first_provider_set = EnsembleSummaryProviderSet(first_provider_dict)
    second_provider_set = EnsembleSummaryProviderSet(second_provider_dict)

    # Metadata for first ensemble mock implementation
    first_ensemble_wwct_a1 = VectorMetadata(
        unit="",
        is_total=False,
        is_rate=True,
        is_historical=False,
        keyword="WWCT",
        wgname="A1",
        get_num=6,
    )
    first_ensemble_wgor_a2 = VectorMetadata(
        unit="SM3/SM3",
        is_total=False,
        is_rate=True,
        is_historical=False,
        keyword="WGOR",
        wgname="A2",
        get_num=7,
    )

    # Metadata for inconsistent ensemble mock implementation
    inconsistent_ensemble_wwct_a1 = VectorMetadata(
        unit="Invalid Unit",
        is_total=False,
        is_rate=False,
        is_historical=False,
        keyword="WWCT",
        wgname="A1",
        get_num=6,
    )
    inconsistent_ensemble_wgor_a2 = VectorMetadata(
        unit="SM3",
        is_total=False,
        is_rate=False,
        is_historical=True,
        keyword="WGOR",
        wgname="A2",
        get_num=7,
    )

    # First provider set should return metadata for the first ensemble mock implementation
    assert first_provider_set.vector_metadata("WWCT:A1") == first_ensemble_wwct_a1
    assert first_provider_set.vector_metadata("WGOR:A2") == first_ensemble_wgor_a2

    # Second provider set should return metadata for the inconsistent ensemble mock implementation
    assert (
        second_provider_set.vector_metadata("WWCT:A1") == inconsistent_ensemble_wwct_a1
    )
    assert (
        second_provider_set.vector_metadata("WGOR:A2") == inconsistent_ensemble_wgor_a2
    )
