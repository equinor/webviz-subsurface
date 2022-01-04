import pytest
from typing import Dict

from webviz_subsurface._providers.ensemble_summary_provider.ensemble_summary_provider import (
    EnsembleSummaryProvider,
    VectorMetadata,
)

from webviz_subsurface.plugins._simulation_time_series.types.provider_set import (
    ProviderSet,
)

from ..mocks.ensemble_summary_provider_mock import (
    FirstEnsembleSummaryProviderMock,
    SecondEnsembleSummaryProviderMock,
    ThirdEnsembleSummaryProviderMock,
    InconsistentEnsembleSummaryProviderMock,
)

TEST_PROVIDER_DICT: Dict[str, EnsembleSummaryProvider] = {
    "First Ensemble": FirstEnsembleSummaryProviderMock(),
    "Second Ensemble": SecondEnsembleSummaryProviderMock(),
    "Third Ensemble": ThirdEnsembleSummaryProviderMock(),
}

TEST_INCONSISTENT_PROVIDER_DICT: Dict[str, EnsembleSummaryProvider] = {
    "First Ensemble": FirstEnsembleSummaryProviderMock(),
    "Third Ensemble": ThirdEnsembleSummaryProviderMock(),
    "Inconsistent ensemble": InconsistentEnsembleSummaryProviderMock(),
}


def test_verify_consistent_vector_metadata() -> None:
    consistent_provider_set = ProviderSet(TEST_PROVIDER_DICT)
    inconsistent_provider_set = ProviderSet(TEST_INCONSISTENT_PROVIDER_DICT)

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
    provider_dict = {
        "First Ensemble": FirstEnsembleSummaryProviderMock(),
        "Second Ensemble": SecondEnsembleSummaryProviderMock(),
    }
    provider_set = ProviderSet(provider_dict)

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
    provider_dict = {
        "First Ensemble": FirstEnsembleSummaryProviderMock(),
        "Second Ensemble": SecondEnsembleSummaryProviderMock(),
    }
    provider_set = ProviderSet(provider_dict)

    # Realizations from first and second mock
    expected_realizations = [1, 2, 3, 4, 5, 8]

    # pylint: disable = protected-access
    created_realizations = provider_set._create_union_of_realizations_from_providers(
        list(provider_dict.values())
    )

    assert created_realizations == expected_realizations


def test_items() -> None:
    provider_set = ProviderSet(TEST_PROVIDER_DICT)
    assert provider_set.items() == TEST_PROVIDER_DICT.items()


def test_names() -> None:
    provider_set = ProviderSet(TEST_PROVIDER_DICT)
    assert provider_set.names() == list(TEST_PROVIDER_DICT.keys())


def test_provider() -> None:
    provider_set = ProviderSet(TEST_PROVIDER_DICT)

    assert isinstance(
        provider_set.provider("First Ensemble"), FirstEnsembleSummaryProviderMock
    )
    assert isinstance(
        provider_set.provider("Second Ensemble"), SecondEnsembleSummaryProviderMock
    )
    assert isinstance(
        provider_set.provider("Third Ensemble"), ThirdEnsembleSummaryProviderMock
    )

    # Expect ValueError when getting invalid provider name
    with pytest.raises(ValueError):
        name = "Invalid Provider"
        provider_set.provider(name)
        pytest.fail(
            f'Expected getting provider "{name}" to fail, as it is not among provider names in set!'
        )


def test_all_providers() -> None:
    provider_set = ProviderSet(TEST_PROVIDER_DICT)
    all_providers = provider_set.all_providers()

    assert len(all_providers) == 3
    assert isinstance(all_providers[0], FirstEnsembleSummaryProviderMock)
    assert isinstance(all_providers[1], SecondEnsembleSummaryProviderMock)
    assert isinstance(all_providers[2], ThirdEnsembleSummaryProviderMock)


def test_all_realizations() -> None:
    provider_set = ProviderSet(TEST_PROVIDER_DICT)
    expected_realizations = [1, 2, 3, 4, 5, 7, 8]

    assert provider_set.all_realizations() == expected_realizations


def test_all_vector_names() -> None:
    provider_set = ProviderSet(TEST_PROVIDER_DICT)

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
    provider_set = ProviderSet(TEST_PROVIDER_DICT)

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
    assert provider_set.vector_metadata("Invalid Vector") == None


def test_vector_metadata_order() -> None:
    """The metadata returns first existing metadata, thereby inconsistent metadata
    will affect result, based on order of the providers in set.
    """
    first_provider_dict = {
        "First Ensemble": FirstEnsembleSummaryProviderMock(),
        "Inconsistent ensemble": InconsistentEnsembleSummaryProviderMock(),
    }
    second_provider_dict = {
        "Inconsistent ensemble": InconsistentEnsembleSummaryProviderMock(),
        "First Ensemble": FirstEnsembleSummaryProviderMock(),
    }

    first_provider_set = ProviderSet(first_provider_dict)
    second_provider_set = ProviderSet(second_provider_dict)

    # Metadata for first ensemble mock implementation
    first_ensemble_WWCT_A1 = VectorMetadata(
        unit="",
        is_total=False,
        is_rate=True,
        is_historical=False,
        keyword="WWCT",
        wgname="A1",
        get_num=6,
    )
    first_ensemble_WGOR_A2 = VectorMetadata(
        unit="SM3/SM3",
        is_total=False,
        is_rate=True,
        is_historical=False,
        keyword="WGOR",
        wgname="A2",
        get_num=7,
    )

    # Metadata for inconsistent ensemble mock implementation
    inconsistent_ensemble_WWCT_A1 = VectorMetadata(
        unit="Invalid Unit",
        is_total=False,
        is_rate=False,
        is_historical=False,
        keyword="WWCT",
        wgname="A1",
        get_num=6,
    )
    inconsistent_ensemble_WGOR_A2 = VectorMetadata(
        unit="SM3",
        is_total=False,
        is_rate=False,
        is_historical=True,
        keyword="WGOR",
        wgname="A2",
        get_num=7,
    )

    # First provider set should return metadata for the first ensemble mock implementation
    assert first_provider_set.vector_metadata("WWCT:A1") == first_ensemble_WWCT_A1
    assert first_provider_set.vector_metadata("WGOR:A2") == first_ensemble_WGOR_A2

    # Second provider set should return metadata for the inconsistent ensemble mock implementation
    assert (
        second_provider_set.vector_metadata("WWCT:A1") == inconsistent_ensemble_WWCT_A1
    )
    assert (
        second_provider_set.vector_metadata("WGOR:A2") == inconsistent_ensemble_WGOR_A2
    )
