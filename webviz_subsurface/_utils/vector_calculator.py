from typing import List, Dict
import pandas as pd

from webviz_config.common_cache import CACHE

from webviz_subsurface_components import (
    VectorCalculator,
    ExpressionInfo,
)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_selected_expressions(
    expressions: List[ExpressionInfo], selected_names: List[str]
) -> List[ExpressionInfo]:
    selected: List[ExpressionInfo] = []
    for name in selected_names:
        selected_expression: ExpressionInfo = next(
            (elm for elm in expressions if elm["name"] == name), None
        )
        if selected_expression is not None and selected_expression not in selected:
            selected.append(selected_expression)
    return selected


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_calculated_vectors(
    expressions: List[ExpressionInfo],
    smry: pd.DataFrame,
) -> pd.DataFrame:
    # TODO: Refactor further
    # Move get_parser_values() and get_expression_with_vector_names into wrapper?
    calculated_vectors: pd.DataFrame = pd.DataFrame()
    for elm in expressions:
        name: str = elm["name"]
        expr: str = elm["expression"]
        var_vec_dict: Dict[str, str] = VectorCalculator.get_var_vec_dict(
            elm["variableVectorMap"]
        )

        values: Dict[str, pd.Series] = {}
        for var in var_vec_dict:
            values[var] = smry[var_vec_dict[var]]

        parsed_expr = VectorCalculator.parse_expression(expr, values)
        if parsed_expr is not None:
            calculated_vectors[name] = parsed_expr
    return calculated_vectors
