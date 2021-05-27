from typing import List, Dict, TypedDict
import numpy as np
import pandas as pd
from py_expression_eval import Parser


class VariableVectorMapInfo(TypedDict):
    variableName: str
    vectorName: List[str]


class ExpressionInfo(TypedDict):
    name: str
    expression: str
    id: str
    variableVectorMap: List[VariableVectorMapInfo]


def get_vector_calculator_parser() -> Parser:
    """Creates expression parser configured to handle vector variables

    Overrides operators to handle vectors by replacing math lib functions with numpy functions

    returns: Configured expression parser
    """
    parser = Parser()
    parser.ops2["^"] = np.power
    parser.functions["log"] = np.log
    return parser


def get_variable_vector_map_as_dict(
    var_vec_map: List[VariableVectorMapInfo],
) -> Dict[str, str]:
    res: dict = {}
    for elm in var_vec_map:
        # TODO verify that elm["variableName"] and elm["vectorName"][0] exists
        res[elm["variableName"]] = elm["vectorName"][0]
    return res


def get_parser_eval_dict(var_vec_dict: Dict[str, str], smry: pd.DataFrame) -> dict:
    res: dict = {}
    for var_name in var_vec_dict:
        res[var_name] = smry[var_vec_dict[var_name]]
    return res


# def set_calculated_vectors(
#     calculated_vectors: pd.DataFrame,
#     expressions: List[ExpressionInfo],
#     expr_parser: Parser,
# ) -> None:


#     return None
