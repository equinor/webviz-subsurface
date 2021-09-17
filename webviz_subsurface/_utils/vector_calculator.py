import sys
from typing import List, Dict, Tuple, Union, Optional

from pathlib import Path
from uuid import uuid4
import yaml
import numpy as np
import pandas as pd

from webviz_config.common_cache import CACHE
from webviz_subsurface_components import (
    VectorCalculator,
    ExpressionInfo,
    ExternalParseData,
    VariableVectorMapInfo,
)

# pylint: disable=ungrouped-imports
if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict

# JSON Schema for predefined expressions configuration
# Used as schema input for json_schema.validate()
PREDEFINED_EXPRESSIONS_JSON_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": {
        "type": "object",
        "required": ["expression", "variableVectorMap"],
        "properties": {
            "expression": {"type": "string", "minLength": 1},
            "description": {
                "type": "string",
                "maxLength": VectorCalculator.max_description_length,
            },
            "variableVectorMap": {
                "type": "object",
                "minProperties": 1,
                "patternProperties": {"^[a-zA-Z]$": {"type": "string"}},
                "additionalProperties": False,
            },
        },
        "additionalProperties": False,
    },
}


class ConfigExpressionDataBase(TypedDict):
    """Base definition for configuration of pre-defined calculated expressions

    `Description`:
    * Simplified data type to pre-define expressions for user.
    * The ConfigExpressionData instance name is the name of the expression - i.e.
    when using a dictionary of ConfigExpressionData the expression name is the dict key

    `Required keys`:
    * expression: str, mathematical expression
    * variableVectorMap: Dict[str,str], Dictionary with {key, value} = {variableName, vectorName}
    """

    expression: str
    variableVectorMap: Dict[str, str]


class ConfigExpressionData(ConfigExpressionDataBase, total=False):
    """
    Type definition for configuration of pre-defined calculated expressions

    `Description`:
    Dictionary type for pre-defined expressions for user.

    `Required keys`:
    * expression: str, mathematical expression
    * variableVectorMap: Dict[str,str], Dictionary with {key, value} = {variableName, vectorName}

    `Non-required keys`:
    * description: str, description of mathematical expression
    """

    description: str


def validate_predefined_expression(
    expression: ExpressionInfo, vector_data: list
) -> Tuple[bool, str]:
    """
    Validates predefined expressions for usage in vector calculator

    Predefined expressions can be defined in configuration file. Validation will ensure valid
    mathematical expression parsing and matching equation variables and variable vector map.
    It will also verify provided vector names in map is represented in provided vector data

    Inputs:
    * expression: Predefined expression
    * vector_data: Vector data

    Returns:
    * Tuple of valid state and validation message. Validation message is empty for valid expression

    """
    parsed_expression: ExternalParseData = VectorCalculator.external_parse_data(
        expression
    )
    expr: str = expression["expression"]
    name: str = expression["name"]

    # Validate expression string
    if not parsed_expression["isValid"]:
        parse_message = parsed_expression["message"]
        message = (
            f'Invalid mathematical expression {expr} in predefined expression "{name}".'
            f"{parse_message}."
        )
        return False, message

    # Match variables in expression string and variable names in map
    expression_variables = parsed_expression["variables"]
    map_variables = [elm["variableName"] for elm in expression["variableVectorMap"]]
    if set(expression_variables) != set(map_variables):
        message = (
            f"Variables {map_variables} in variableVectorMap is inconsistent with variables "
            f'{expression_variables} in equation "{expr}" for predefined expression "{name}"'
        )
        return False, message

    # Validate vector names
    variable_vector_dict = VectorCalculator.variable_vector_dict(
        expression["variableVectorMap"]
    )
    invalid_vectors: List[str] = []
    for vector_name in variable_vector_dict.values():
        if not is_vector_name_existing(vector_name, vector_data):
            invalid_vectors.append(vector_name)
    if len(invalid_vectors) > 1:
        message = (
            f'Vector names {invalid_vectors} in predefined expression "{name}" are not'
            f" represented in vector data"
        )
        return False, message
    if len(invalid_vectors) > 0:
        message = (
            f'Vector name {invalid_vectors} in predefined expression "{name}" is not'
            f" represented in vector data"
        )
        return False, message

    return True, ""


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


def expressions_from_config(
    predefined_expressions: Optional[Path],
) -> List[ExpressionInfo]:
    output: List[ExpressionInfo] = []

    if predefined_expressions is None:
        return output

    expressions: Dict[str, ConfigExpressionData] = yaml.safe_load(
        predefined_expressions.read_text()
    )

    for expression in expressions:
        expression_dict = {
            "name": expression,
            "expression": expressions[expression]["expression"],
            "id": f"{uuid4()}",
            "variableVectorMap": variable_vector_map_from_dict(
                expressions[expression]["variableVectorMap"]
            ),
            "isValid": False,  # Set False and validate in seperate operation
            "isDeletable": False,
        }
        if "description" in expressions[expression].keys():
            expression_dict["description"] = expressions[expression]["description"]

        output.append(expression_dict)
    return output


def is_vector_name_existing(name: str, vector_data: list) -> bool:
    nodes = name.split(":")
    current_child_list = vector_data
    for node in nodes:
        found = False
        for child in current_child_list:
            if child["name"] == node:
                children = child["children"]
                current_child_list = children if children is not None else []
                found = True
                break
        if not found:
            return False
    return found


def get_expression_from_name(
    name: str, expressions: List[ExpressionInfo]
) -> Union[ExpressionInfo, None]:
    for expr in expressions:
        if name == expr["name"]:
            return expr
    return None


def get_custom_vector_definitions_from_expressions(
    expressions: List[ExpressionInfo],
) -> dict:
    """
    Get custom vector definitions for vector selector from list of calculated expressions.

    VectorSelector has VectorDefinitions which is utilized for calculated expressions.

    `VectorDefinitions:`
        key: str, vector name
        value: {
            type: str, defined vector type
            description: str, description of vector
        }

    `Note:`
    Uses expression str as description if optional expression description str does not exist.
    """

    output: dict = {}
    for expression in expressions:
        name = expression["name"]
        vector_type = "calculated"
        description = (
            expression["expression"]
            if not "description" in dict(expression).keys()
            else expression["description"]
        )
        output[name] = {"type": vector_type, "description": description}
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


def get_calculated_vector_df(
    expression: ExpressionInfo, smry: pd.DataFrame, ensembles: List[str]
) -> pd.DataFrame:
    columns = ["REAL", "ENSEMBLE", "DATE"]

    name: str = expression["name"]
    expr: str = expression["expression"]

    var_vec_dict: Dict[str, str] = VectorCalculator.variable_vector_dict(
        expression["variableVectorMap"]
    )
    vector_names = var_vec_dict.values()

    # Retreive vectors for calculating expression - filtered on ensembles
    df = smry[columns + list(vector_names)].copy()
    df = df[df["ENSEMBLE"].isin(ensembles)]

    values: Dict[str, np.ndarray] = {}
    for variable, vector in var_vec_dict.items():
        values[variable] = df[vector].values

    evaluated_expr = VectorCalculator.evaluate_expression(expr, values)
    if evaluated_expr is not None:
        df[name] = evaluated_expr

    return df[columns + [name]]


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
        except ValueError:
            continue
    return calculated_units
