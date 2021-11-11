import sys
from typing import Dict, List

from webviz_subsurface._providers import EnsembleSummaryProvider

from .provider_set import ProviderSet
from .types import (
    DeltaEnsembleProvider,
    DeltaEnsembleNamePair,
    create_delta_ensemble_name,
)

from ..._abbreviations.reservoir_simulation import (
    simulation_vector_description,
    simulation_unit_reformat,
)


def create_vector_plot_title(provider_set: ProviderSet, vector_name: str) -> str:
    if sys.version_info >= (3, 9):
        vector_filtered = vector_name.removeprefix("AVG_").removeprefix("INTVL_")
    else:
        vector_filtered = (
            vector_name[4:]
            if vector_name.startswith("AVG_")
            else (vector_name[6:] if vector_name.startswith("INTVL_") else vector_name)
        )

    metadata = provider_set.vector_metadata(vector_filtered)

    if metadata is None:
        return simulation_vector_description(vector_name)

    unit = metadata.get("unit", "")
    if unit:
        return (
            f"{simulation_vector_description(vector_name)}"
            f" [{simulation_unit_reformat(unit)}]"
        )
    return f"{simulation_vector_description(vector_name)}"


def create_selected_provider_set(
    input_provider_set: ProviderSet,
    selected_ensembles: List[str],
    delta_ensemble_name_pairs: List[DeltaEnsembleNamePair],
) -> ProviderSet:
    """
    Function to create a provider set based on selected ensemble names

    By use of an input provider set, the providers for delta ensemble can be
    created.

    `Note:` If delta ensemble requires provider not among input provider set,
    an exception is raised!

    `Input:`
    * input_provider_set: ProviderSet - Set of providers used as base for selectable
    provider set, e.g. providers from a factory.
    * selected_ensembles: List[str] - List of selected ensemble provider names
    * delta_ensembles: List[DeltaEnsembleNamePair] - List of existing delta ensemble name pairs,
    used for matching among selected ensemble names

    `Return:`
    * ProviderSet with selected input providers and selected delta ensembles created by
    delta ensemble name pairs among the input provider set.
    """
    _selected_provider_dict: Dict[str, EnsembleSummaryProvider] = {
        name: provider
        for name, provider in input_provider_set.items()
        if name in selected_ensembles
    }
    for name_pair in delta_ensemble_name_pairs:
        delta_ensemble_name = create_delta_ensemble_name(name_pair)
        if (
            delta_ensemble_name in selected_ensembles
            and delta_ensemble_name not in _selected_provider_dict
        ):
            _selected_provider_dict[
                delta_ensemble_name
            ] = create_delta_ensemble_provider(name_pair, input_provider_set)

    return ProviderSet(_selected_provider_dict)


def create_delta_ensemble_provider(
    delta_ensemble_name_pair: DeltaEnsembleNamePair,
    input_provider_set: ProviderSet,
) -> DeltaEnsembleProvider:
    """
    Create delta ensemble summary provider by use of delta ensemble name pair
    and set of providers.

    `Input:`
    * delta_ensemble_name_pair: DeltaEnsembleNamePair - Name pair, i.e. name of
    ensemble A and ensemble B
    * input_provider_set: ProviderSet - Set of input providers which a
    delta ensemble can be created from

    `Return:`
    * DeltaEnsemble created on delta ensemble name pair. If one or more ensemble
    in name pair does not exist among input provider set, exception is raised
    """
    ensemble_a = delta_ensemble_name_pair["ensemble_a"]
    ensemble_b = delta_ensemble_name_pair["ensemble_b"]
    provider_set_ensembles = input_provider_set.names()
    if (
        ensemble_a not in provider_set_ensembles
        or ensemble_b not in provider_set_ensembles
    ):
        raise ValueError(
            f"Request delta ensemble with ensemble {ensemble_a}"
            f" and ensemble {ensemble_b}. Ensemble {ensemble_a} exists: "
            f"{ensemble_a in provider_set_ensembles}, ensemble {ensemble_b} exists: "
            f"{ensemble_b in provider_set_ensembles}."
        )
    return DeltaEnsembleProvider(
        input_provider_set.provider(ensemble_a),
        input_provider_set.provider(ensemble_b),
    )
