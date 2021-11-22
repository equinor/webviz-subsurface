import sys
from typing import Dict, List, Optional
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

from webviz_subsurface._utils.vector_calculator import (
    ExpressionInfo,
    VectorCalculator,
    get_expression_from_name,
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


def create_vector_plot_titles_from_provider_set(
    vector_names: List[str],
    expressions: List[ExpressionInfo],
    provider_set: ProviderSet,
) -> Dict[str, str]:
    """Create plot titles for vectors

    Create plot titles for vectors by use of provider set metadata and list of
    calculation expressions

    `Return:`
    * Dictionary with vector names as keys and the corresponding title as value
    """
    vector_title_dict: Dict[str, str] = {}

    all_vector_names = provider_set.all_vector_names()
    for vector_name in vector_names:
        vector = vector_name

        if vector.startswith("AVG_"):
            vector = vector.lstrip("AVG_")
        if vector.startswith("INTVL_"):
            vector = vector.lstrip("INTVL_")

        if vector in all_vector_names:
            metadata = provider_set.vector_metadata(vector)
            title = simulation_vector_description(vector_name)
            if metadata and metadata.unit:
                title = (
                    f"{simulation_vector_description(vector_name)}"
                    f" [{simulation_unit_reformat(metadata.unit)}]"
                )
            vector_title_dict[vector_name] = title
        else:
            expression = get_expression_from_name(vector_name, expressions)
            if expression:
                unit = create_calculated_unit_from_provider_set(
                    expression, provider_set
                )
                if unit:
                    # TODO: Expression description instead of vector name in title?
                    vector_title_dict[vector_name] = f"{vector_name} [{unit}]"
                else:
                    vector_title_dict[vector_name] = vector_name
            else:
                vector_title_dict[vector_name] = vector_name
    return vector_title_dict


def create_calculated_unit_from_provider_set(
    expression: ExpressionInfo, provider_set: ProviderSet
) -> Optional[str]:
    try:
        # Parse only for validation
        VectorCalculator.parser.parse(expression["expression"])
        unit_expr: str = expression["expression"]
        for elm in expression["variableVectorMap"]:
            metadata = provider_set.vector_metadata(elm["vectorName"][0])
            if metadata and metadata.unit:
                unit_expr = unit_expr.replace(elm["variableName"], metadata.unit)

        return unit_expr
    except ValueError:
        return None


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
