from typing import List, Dict
import pandas as pd
import sys

if sys.version_info[0] == 3 and sys.version_info[1] >= 8:
    from typing import TypedDict
else:
    from typing_extensions import TypedDict

from uuid import uuid4

from webviz_config.common_cache import CACHE
from webviz_subsurface_components import (
    VectorCalculator,
    ExpressionInfo,
    VariableVectorMapInfo,
)


class ConfigExpressionData(TypedDict):
    """Type definition for configuration of pre-defined calculated expressions

    Simplified data type to pre-define expressions for user.

    The ConfigExpressionData instance name is the name of the expression - i.e.
    when using a dictionary of ConfigExpressionData the expression name is the dict key

    expression: str, mathematical expression
    variableVectorMap: Dict[str,str], Dictionary with {key, value} = {variableName, vectorName}
    """

    expression: str
    variableVectorMap: Dict[str, str]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def variable_vector_map_from_dict(
    variable_vector_dict: Dict[str, str]
) -> List[VariableVectorMapInfo]:
    variable_vector_map: List[VariableVectorMapInfo] = []
    for variable in variable_vector_dict:
        variable_vector_map.append(
            {
                "variableName": variable,
                "vectorName": [variable_vector_dict[variable]],
            }
        )
    return variable_vector_map


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def expressions_from_config(
    expressions: Dict[str, ConfigExpressionData],
) -> List[ExpressionInfo]:
    output: List[ExpressionInfo] = []

    for expression in expressions:
        output.append(
            {
                "name": expression,
                "expression": expressions[expression]["expression"],
                "id": f"{uuid4()}",
                "variableVectorMap": variable_vector_map_from_dict(
                    expressions[expression]["variableVectorMap"]
                ),
                "isValid": True,
                "isDeletable": False,
            }
        )
    return output


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
    calculated_vectors: pd.DataFrame = pd.DataFrame()
    for elm in expressions:
        name: str = elm["name"]
        expr: str = elm["expression"]
        var_vec_dict: Dict[str, str] = VectorCalculator.variable_vector_dict(
            elm["variableVectorMap"]
        )

        values: Dict[str, pd.Series] = {}
        for var in var_vec_dict:
            values[var] = smry[var_vec_dict[var]]

        evaluated_expr = VectorCalculator.evaluate_expression(expr, values)
        if evaluated_expr is not None:
            calculated_vectors[name] = evaluated_expr
    return calculated_vectors


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_calculated_units(
    expressions: List[ExpressionInfo],
    units: pd.Series,
) -> pd.Series:
    # TODO Update expression handling
    # Future: check equal equal unit on each vector:
    # - if equal unit on + or -: x[m]+y[m] = [m]
    # - If unequal unit on + or -: Set unit "mixed"?
    # - *, / or ^: perform operators on units
    #
    # Utilize ./_datainput/units.py and/or ./_datainput/eclipse_unit.py
    #
    #
    # Now: parse expression str with VectorCalculator.parser.parse()
    # if valid, do string replace with units from smry_meta
    calculated_units: pd.Series = pd.Series()

    for expression in expressions:
        try:
            # Parse only for validation
            VectorCalculator.parser.parse(expression["expression"])
            unit_expr: str = expression["expression"]
            for elm in expression["variableVectorMap"]:
                unit_expr = unit_expr.replace(
                    elm["variableName"], units[elm["vectorName"][0]]
                )

            calculated_units[expression["name"]] = unit_expr
        except:
            continue
    return calculated_units
