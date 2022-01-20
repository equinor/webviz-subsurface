from typing import Dict, List, Optional

from webviz_subsurface._abbreviations.reservoir_simulation import (
    simulation_unit_reformat,
    simulation_vector_description,
)
from webviz_subsurface._utils.vector_calculator import (
    ExpressionInfo,
    VectorCalculator,
    get_expression_from_name,
)
from webviz_subsurface.plugins._simulation_time_series.utils.from_timeseries_cumulatives import (
    get_cumulative_vector_name,
    is_interval_or_average_vector,
)

from ..types import ProviderSet


def create_vector_plot_titles_from_provider_set(
    vector_names: List[str],
    expressions: List[ExpressionInfo],
    provider_set: ProviderSet,
    user_defined_vector_descriptions: Dict[str, str],
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
            title = user_defined_vector_descriptions.get(
                vector_name.split(":")[0], simulation_vector_description(vector_name)
            )
            if metadata and metadata.unit:
                title += f" [{simulation_unit_reformat(metadata.unit)}]"
            vector_title_dict[vector_name] = title

        # INTVL_ or AVG_ vector
        elif is_interval_or_average_vector(vector_name):
            vector = vector_name
            cumulative_vector = get_cumulative_vector_name(vector_name)
            title = ""
            if vector.startswith("AVG_"):
                vector = vector.lstrip("AVG_")
                title = user_defined_vector_descriptions.get(
                    cumulative_vector.split(":")[0], ""
                )
                title = (
                    title + "Per Day"
                    if title
                    else simulation_vector_description(vector)
                )

            if vector.startswith("INTVL_"):
                vector = vector.lstrip("INTVL_")
                title = user_defined_vector_descriptions.get(
                    cumulative_vector.split(":")[0],
                    simulation_vector_description(vector),
                )

            metadata = provider_set.vector_metadata(vector)
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
