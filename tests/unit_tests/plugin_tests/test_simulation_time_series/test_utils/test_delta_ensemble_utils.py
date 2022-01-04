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

from ..mocks.ensemble_summary_provider_mock import (
    FirstEnsembleSummaryProviderMock,
    SecondEnsembleSummaryProviderMock,
    ThirdEnsembleSummaryProviderMock,
)


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
    provider_set = ProviderSet(
        {
            "First Ensemble": FirstEnsembleSummaryProviderMock(),
            "Second Ensemble": SecondEnsembleSummaryProviderMock(),
        }
    )

    valid_delta_ensemble = DeltaEnsemble(
        ensemble_a="First Ensemble", ensemble_b="Second Ensemble"
    )
    invalid_delta_ensemble = DeltaEnsemble(
        ensemble_a="First Ensemble", ensemble_b="Third Ensemble"
    )

    assert is_delta_ensemble_providers_in_provider_set(
        valid_delta_ensemble, provider_set
    )
    assert not is_delta_ensemble_providers_in_provider_set(
        invalid_delta_ensemble, provider_set
    )


def test_create_delta_ensemble_provider_pair() -> None:
    provider_set = ProviderSet(
        {
            "First Ensemble": FirstEnsembleSummaryProviderMock(),
            "Second Ensemble": SecondEnsembleSummaryProviderMock(),
            "Third Ensemble": ThirdEnsembleSummaryProviderMock(),
        }
    )

    first_delta_ensemble = DeltaEnsemble(
        ensemble_a="First Ensemble", ensemble_b="Third Ensemble"
    )
    second_delta_ensemble = DeltaEnsemble(
        ensemble_a="Third Ensemble", ensemble_b="Second Ensemble"
    )

    first_provider_pair = create_delta_ensemble_provider_pair(
        first_delta_ensemble, provider_set
    )
    second_provider_pair = create_delta_ensemble_provider_pair(
        second_delta_ensemble, provider_set
    )

    assert len(first_provider_pair) == 2
    assert isinstance(first_provider_pair[0], FirstEnsembleSummaryProviderMock)
    assert isinstance(first_provider_pair[1], ThirdEnsembleSummaryProviderMock)

    assert len(second_provider_pair) == 2
    assert isinstance(second_provider_pair[0], ThirdEnsembleSummaryProviderMock)
    assert isinstance(second_provider_pair[1], SecondEnsembleSummaryProviderMock)


def test_create_delta_ensemble_provider_pair_invalid_ensemble() -> None:
    provider_set = ProviderSet(
        {
            "First Ensemble": FirstEnsembleSummaryProviderMock(),
            "Second Ensemble": SecondEnsembleSummaryProviderMock(),
        }
    )

    # Expect ValueError when retrieveing ensemble_b is invalid
    with pytest.raises(ValueError):
        invalid_ensemble = "Invalid Ensemble"
        invalid_provider_pair = DeltaEnsemble(
            ensemble_a="First Ensemble", ensemble_b=invalid_ensemble
        )
        create_delta_ensemble_provider_pair(invalid_provider_pair, provider_set)
        pytest.fail(
            "Expected ValueError when creating delta ensemble provider pair, as ensemble b = "
            f'"{invalid_ensemble}" is not existing in provider set!'
        )
