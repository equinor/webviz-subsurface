from typing import Dict, List, Optional

from webviz_subsurface_components.py_expression_eval import ParserError

from webviz_subsurface._abbreviations.reservoir_simulation import (
    simulation_unit_reformat,
    simulation_vector_description,
)
from webviz_subsurface._utils.vector_calculator import (
    ExpressionInfo,
    VectorCalculator,
    get_expression_from_name,
)

from ..types import ProviderSet


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
    except ParserError:
        return None
