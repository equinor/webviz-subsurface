import sys
from typing import Dict, List
from pathlib import Path

from webviz_subsurface._abbreviations.reservoir_simulation import (
    simulation_vector_description,
    simulation_unit_reformat,
)
from webviz_subsurface._providers import (
    EnsembleSummaryProvider,
    EnsembleSummaryProviderFactory,
    Frequency,
)

from ..types import (
    create_delta_ensemble_name,
    DeltaEnsembleProvider,
    DeltaEnsembleNamePair,
    ProviderSet,
)


def create_lazy_provider_set_from_paths(
    name_path_dict: Dict[str, Path],
) -> ProviderSet:
    provider_factory = EnsembleSummaryProviderFactory.instance()
    provider_dict: Dict[str, EnsembleSummaryProvider] = {}
    for name, path in name_path_dict.items():
        provider_dict[name] = provider_factory.create_from_arrow_unsmry_lazy(str(path))
    return ProviderSet(provider_dict)


def create_presampled_provider_set_from_paths(
    name_path_dict: Dict[str, Path],
    presampling_frequency: Frequency,
) -> ProviderSet:
    # TODO: Make presampling_frequency: Optional[Frequency] when allowing raw data for plugin
    provider_factory = EnsembleSummaryProviderFactory.instance()
    provider_dict: Dict[str, EnsembleSummaryProvider] = {}
    for name, path in name_path_dict.items():
        provider_dict[name] = provider_factory.create_from_arrow_unsmry_presampled(
            str(path), presampling_frequency
        )
    return ProviderSet(provider_dict)


def create_vector_plot_title_from_provider_set(
    provider_set: ProviderSet, vector_name: str
) -> str:
    """Create plot title for vector by use of provider set

    Retrives metadata from provider set and creates plot title base

    `Returns:`
    Plot title for vector in provider set.
    """
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

    if metadata.unit:
        return (
            f"{simulation_vector_description(vector_name)}"
            f" [{simulation_unit_reformat(metadata.unit)}]"
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
    * delta_ensemble_name_pairs: List[DeltaEnsembleNamePair] - List of existing delta
    ensemble name pairs, used to extract and create selected delta ensembles

    `Return:`
    * ProviderSet with selected input providers and delta ensembles created by use of
    selected ensemble names, delta ensemble name pairs and the input provider set.
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
            ] = create_delta_ensemble_provider_from_provider_set(
                name_pair, input_provider_set
            )

    return ProviderSet(_selected_provider_dict)


def create_delta_ensemble_provider_from_provider_set(
    delta_ensemble_name_pair: DeltaEnsembleNamePair,
    provider_set: ProviderSet,
) -> DeltaEnsembleProvider:
    """
    Create delta ensemble summary provider by use of delta ensemble name pair
    and set of providers.

    `Input:`
    * delta_ensemble_name_pair: DeltaEnsembleNamePair - Name pair, i.e. name of
    ensemble A and ensemble B
    * provider_set: ProviderSet - Set of providers which a delta ensemble can
    be created from

    `Return:`
    * DeltaEnsemble created on delta ensemble name pair. If one or more ensemble
    name in name pair does not exist in provider set, exception is raised
    """
    name_a = delta_ensemble_name_pair["ensemble_a"]
    name_b = delta_ensemble_name_pair["ensemble_b"]
    provider_names = provider_set.names()
    if name_a not in provider_names or name_b not in provider_names:
        raise ValueError(
            f"Request delta ensemble with ensemble {name_a}"
            f" and ensemble {name_b}. Ensemble {name_a} exists: "
            f"{name_a in provider_names}, ensemble {name_b} exists: "
            f"{name_b in provider_names}."
        )
    return DeltaEnsembleProvider(
        provider_set.provider(name_a),
        provider_set.provider(name_b),
    )
