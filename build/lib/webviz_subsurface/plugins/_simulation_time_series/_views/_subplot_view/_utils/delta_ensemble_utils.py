from typing import Dict, List, Tuple

from webviz_subsurface._providers import EnsembleSummaryProvider
from webviz_subsurface._utils.ensemble_summary_provider_set import (
    EnsembleSummaryProviderSet,
)

from .._types import DeltaEnsemble


def create_delta_ensemble_name(delta_ensemble: DeltaEnsemble) -> str:
    """Create delta ensemble name from delta ensemble"""
    name_a = delta_ensemble["ensemble_a"]
    name_b = delta_ensemble["ensemble_b"]
    return f"({name_a})-({name_b})"


def create_delta_ensemble_names(delta_ensembles: List[DeltaEnsemble]) -> List[str]:
    """Create list of delta ensemble names form list of delta ensembles"""
    return [
        create_delta_ensemble_name(delta_ensemble) for delta_ensemble in delta_ensembles
    ]


def create_delta_ensemble_name_dict(
    delta_ensembles: List[DeltaEnsemble],
) -> Dict[str, DeltaEnsemble]:
    """Create dictionary with delta ensemble name as key and and corresponding delta ensemble
    as value, from list if delta ensembles"""
    return {
        create_delta_ensemble_name(delta_ensemble): delta_ensemble
        for delta_ensemble in delta_ensembles
    }


def is_delta_ensemble_providers_in_provider_set(
    delta_ensemble: DeltaEnsemble, provider_set: EnsembleSummaryProviderSet
) -> bool:
    """Check if the delta ensemble providers exist in provider set

    `Returns:`
    * True if name of ensemble A and ensemble B exist among provider set names,
    false otherwise
    """
    return (
        delta_ensemble["ensemble_a"] in provider_set.provider_names()
        and delta_ensemble["ensemble_b"] in provider_set.provider_names()
    )


def create_delta_ensemble_provider_pair(
    delta_ensemble: DeltaEnsemble, provider_set: EnsembleSummaryProviderSet
) -> Tuple[EnsembleSummaryProvider, EnsembleSummaryProvider]:
    """Create pair of providers representing a delta ensemble

    `Return:`
    * Return Tuple with provider for ensemble A and ensemble B in a delta ensemble
    retrieved from provider set. If one or more provider does not exist, exception
    is raised!
    """

    ensemble_a = delta_ensemble["ensemble_a"]
    ensemble_b = delta_ensemble["ensemble_b"]
    if not is_delta_ensemble_providers_in_provider_set(delta_ensemble, provider_set):
        provider_names = provider_set.provider_names()
        raise ValueError(
            f"Request delta ensemble with ensemble {ensemble_a}"
            f" and ensemble {ensemble_b}. Ensemble {ensemble_a} exists: "
            f"{ensemble_a in provider_names}, ensemble {ensemble_b} exists: "
            f"{ensemble_b in provider_names}."
        )
    return (provider_set.provider(ensemble_a), provider_set.provider(ensemble_b))
