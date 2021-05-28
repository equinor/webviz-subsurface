from typing import List, Dict
import pandas as pd
from webviz_subsurface_components import (
    VectorCalculator,
    ExpressionInfo,
    VariableVectorMapInfo,
)


def get_expression_with_vector_names(expression: ExpressionInfo) -> str:
    res: str = expression["expression"]
    var_vec_map: List[VariableVectorMapInfo] = expression["variableVectorMap"]
    for var_vec_pair in var_vec_map:
        res = res.replace(var_vec_pair["variableName"], var_vec_pair["vectorName"][0])
    return res


def get_parser_values(
    var_vec_dict: Dict[str, str], smry: pd.DataFrame
) -> Dict[str, pd.Series]:
    res: Dict[str, pd.Series] = {}
    for var_name in var_vec_dict:
        res[var_name] = smry[var_vec_dict[var_name]]
    return res


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
        var_vec_map = elm["variableVectorMap"]

        values: Dict[str, pd.Series] = get_parser_values(
            VectorCalculator.get_var_vec_dict(var_vec_map), smry
        )
        parsed_expr = VectorCalculator.parse_expression(expr, values)
        if parsed_expr is not None:
            calculated_vectors[name] = parsed_expr
    return calculated_vectors
