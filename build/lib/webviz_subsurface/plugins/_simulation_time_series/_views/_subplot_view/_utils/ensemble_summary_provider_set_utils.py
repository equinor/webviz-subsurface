from typing import Dict, List, Optional

from webviz_subsurface_components import VectorDefinition
from webviz_subsurface_components.py_expression_eval import ParserError

from webviz_subsurface._abbreviations.reservoir_simulation import (
    simulation_unit_reformat,
    simulation_vector_description,
)
from webviz_subsurface._providers import Frequency
from webviz_subsurface._utils.ensemble_summary_provider_set import (
    EnsembleSummaryProviderSet,
)
from webviz_subsurface._utils.vector_calculator import (
    ExpressionInfo,
    VectorCalculator,
    get_expression_from_name,
)

from .from_timeseries_cumulatives import (
    get_cumulative_vector_name,
    is_per_interval_or_per_day_vector,
)


def create_vector_plot_titles_from_provider_set(
    vector_names: List[str],
    expressions: List[ExpressionInfo],
    provider_set: EnsembleSummaryProviderSet,
    user_defined_vector_definitions: Dict[str, VectorDefinition],
    resampling_frequency: Optional[Frequency] = None,
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

        # Provider vector
        if vector_name in all_vector_names:
            metadata = provider_set.vector_metadata(vector_name)
            title = simulation_vector_description(
                vector_name, user_defined_vector_definitions
            )
            if metadata and metadata.unit:
                title += f" [{simulation_unit_reformat(metadata.unit)}]"
            vector_title_dict[vector_name] = title

        # Per Interval or Per Day vector
        elif is_per_interval_or_per_day_vector(vector_name):
            title = simulation_vector_description(
                vector_name, user_defined_vector_definitions
            )

            cumulative_vector = get_cumulative_vector_name(vector_name)
            metadata = provider_set.vector_metadata(cumulative_vector)
            if resampling_frequency:
                title = f"{str(resampling_frequency.value).capitalize()} " + title
            if vector_name.startswith("PER_DAY_"):
                if metadata and metadata.unit:
                    _unit = metadata.unit + "/DAY"
                    title += f" [{simulation_unit_reformat(_unit)}]"
            if vector_name.startswith("PER_INTVL_"):
                if metadata and metadata.unit:
                    title += f" [{simulation_unit_reformat(metadata.unit)}]"
            vector_title_dict[vector_name] = title

        # Calculated vector
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
    expression: ExpressionInfo, provider_set: EnsembleSummaryProviderSet
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
    except ParserError:
        return None
