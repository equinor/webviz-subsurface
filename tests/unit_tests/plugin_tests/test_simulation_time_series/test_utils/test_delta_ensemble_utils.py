import pytest

from webviz_subsurface.plugins._simulation_time_series.types.provider_set import (
    ProviderSet,
)
from webviz_subsurface.plugins._simulation_time_series.utils.delta_ensemble_utils import (
    create_delta_ensemble_name,
    create_delta_ensemble_name_dict,
    create_delta_ensemble_names,
    create_delta_ensemble_provider_pair,
    is_delta_ensemble_providers_in_provider_set,
    DeltaEnsemble,
)

from ..mocks.ensemble_summary_provider_mock import EnsembleSummaryProviderMock


def test_create_delta_ensemble_name() -> None:
    assert "(first name)-(second name)" == create_delta_ensemble_name(
        DeltaEnsemble(ensemble_a="first name", ensemble_b="second name")
    )
    assert "(first-Name)-(second-Name)" == create_delta_ensemble_name(
        DeltaEnsemble(ensemble_a="first-Name", ensemble_b="second-Name")
    )
    assert "(ens-0)-(ens-3)" == create_delta_ensemble_name(
        DeltaEnsemble(ensemble_a="ens-0", ensemble_b="ens-3")
    )


def test_create_delta_ensemble_names() -> None:
    first_delta_ensemble = DeltaEnsemble(ensemble_a="first name", ensemble_b="second name")
    second_delta_ensemble = DeltaEnsemble(ensemble_a="first-Name", ensemble_b="second-Name")
    third_delta_ensemble = DeltaEnsemble(ensemble_a="ens-0", ensemble_b="ens-3")

    assert create_delta_ensemble_names(
        [first_delta_ensemble, second_delta_ensemble, third_delta_ensemble]
    ) == ["(first name)-(second name)", "(first-Name)-(second-Name)", "(ens-0)-(ens-3)"]


def test_create_delta_ensemble_name_dict() -> None:
    first_delta_ensemble = DeltaEnsemble(ensemble_a="first name", ensemble_b="second name")
    second_delta_ensemble = DeltaEnsemble(ensemble_a="first-Name", ensemble_b="second-Name")
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
    provider_set = ProviderSet(
        {
            "First provider": EnsembleSummaryProviderMock.create_mock_with_first_dataset(),
            "Second provider": EnsembleSummaryProviderMock.create_mock_with_second_dataset(),
        }
    )

    valid_delta_ensemble = DeltaEnsemble(ensemble_a="First provider", ensemble_b="Second provider")
    invalid_delta_ensemble = DeltaEnsemble(ensemble_a="First provider", ensemble_b="Third provider")

    assert is_delta_ensemble_providers_in_provider_set(valid_delta_ensemble, provider_set)
    assert not is_delta_ensemble_providers_in_provider_set(invalid_delta_ensemble, provider_set)


def test_create_delta_ensemble_provider_pair() -> None:
    provider_set = ProviderSet(
        {
            "First provider": EnsembleSummaryProviderMock.create_mock_with_first_dataset(),
            "Second provider": EnsembleSummaryProviderMock.create_mock_with_second_dataset(),
            "Third provider": EnsembleSummaryProviderMock.create_mock_with_third_dataset(),
        }
    )

    first_delta_ensemble = DeltaEnsemble(ensemble_a="First provider", ensemble_b="Third provider")
    second_delta_ensemble = DeltaEnsemble(ensemble_a="Third provider", ensemble_b="Second provider")

    first_provider_pair = create_delta_ensemble_provider_pair(first_delta_ensemble, provider_set)
    second_provider_pair = create_delta_ensemble_provider_pair(second_delta_ensemble, provider_set)

    assert len(first_provider_pair) == 2
    ensemble_a: EnsembleSummaryProviderMock = first_provider_pair[0]
    ensemble_b: EnsembleSummaryProviderMock = first_provider_pair[1]
    assert ensemble_a.get_dataset_name() == "First dataset"
    assert ensemble_b.get_dataset_name() == "Third dataset"

    assert len(second_provider_pair) == 2
    ensemble_a = second_provider_pair[0]
    ensemble_b = second_provider_pair[1]
    assert ensemble_a.get_dataset_name() == "Third dataset"
    assert ensemble_b.get_dataset_name() == "Second dataset"


def test_create_delta_ensemble_provider_pair_invalid_ensemble() -> None:
    provider_set = ProviderSet(
        {
            "First provider": EnsembleSummaryProviderMock.create_mock_with_first_dataset(),
            "Second provider": EnsembleSummaryProviderMock.create_mock_with_second_dataset(),
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
